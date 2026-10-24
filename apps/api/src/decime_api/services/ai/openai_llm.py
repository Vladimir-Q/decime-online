import json
import logging
import time
from pathlib import Path

from decime_api.schemas.compose import ReplyBundle, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest, UnderstandTextResponse
from decime_api.services.ai.lc.orchestrator import require_langchain_for_text
from decime_api.services.ai.lc.prompt_provider import render_prompt
from decime_api.services.ai.llm_json_schemas import (
    reply_bundle_json_schema,
    understand_text_json_schema,
)
from decime_api.services.ai.reply_language import spanish_reply_contaminated
from decime_api.services.compose.dialect_stamp import build_dialect_stamp

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "translate_to_esuy.md"
UNDERSTAND_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "understand_incoming.md"


def _translate_payload(request: TranslateToEsRequest) -> str:
    user_payload = {
        "source_language": request.source_language,
        "source_text": request.source_text,
        "context": request.context.model_dump(exclude_none=True),
    }
    return json.dumps(user_payload, ensure_ascii=False, indent=2)


def _translate_user_content(request: TranslateToEsRequest, *, reinforce_spanish: bool) -> str:
    _system, human, _identity = render_prompt(
        "translate_to_esuy",
        reinforce_spanish=reinforce_spanish,
        level_is_a2=request.context.user_level == "A2",
        payload_json=_translate_payload(request),
    )
    return human


def _understand_payload(request: UnderstandTextRequest) -> str:
    user_payload = {
        "source_text": request.source_text,
        "source_language": request.source_language,
        "target_language": request.target_language,
        "locale_variant": request.locale_variant,
        "channel": request.channel,
    }
    return json.dumps(user_payload, ensure_ascii=False, indent=2)


def _understand_user_content(request: UnderstandTextRequest) -> str:
    _system, human, _identity = render_prompt(
        "understand_incoming",
        target_is_ru=request.target_language == "ru",
        payload_json=_understand_payload(request),
    )
    return human


class OpenAILLMProvider:
    """Text LLM via LangChain ChatOpenAI (official OpenAI or compatible base_url)."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url
        self.last_usage: dict | None = None

    async def translate_to_esuy(self, request: TranslateToEsRequest) -> ReplyBundle:
        from decime_api.services.analytics.llm_usage import merge_usage_snapshots

        require_langchain_for_text()
        self.last_usage = None
        started = time.perf_counter()
        bundle, usage = await self._translate_once(request, reinforce_spanish=False)
        if spanish_reply_contaminated(
            source_language=request.source_language,
            source_text=request.source_text,
            reply_text=bundle.recommended_reply,
        ):
            logger.warning(
                "translate_to_esuy returned source-language text; retrying with Spanish reinforcement"
            )
            bundle, usage_retry = await self._translate_once(request, reinforce_spanish=True)
            usage = merge_usage_snapshots(usage, usage_retry)
        self.last_usage = usage

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "translate_to_esuy provider=%s model=%s orchestrator=langchain latency_ms=%s",
            self.provider_name,
            self.model_name,
            latency_ms,
        )
        return bundle

    async def _translate_once(
        self,
        request: TranslateToEsRequest,
        *,
        reinforce_spanish: bool,
    ) -> tuple[ReplyBundle, dict]:
        from decime_api.services.ai.lc.structured_chat import ainvoke_structured
        from decime_api.services.analytics.llm_usage import log_llm_usage, usage_snapshot
        from decime_api.services.analytics.request_context import get_current_user_id

        system_prompt, user_content, identity = render_prompt(
            "translate_to_esuy",
            reinforce_spanish=reinforce_spanish,
            level_is_a2=request.context.user_level == "A2",
            payload_json=_translate_payload(request),
        )
        result = await ainvoke_structured(
            operation="translate_to_esuy",
            system_prompt=system_prompt,
            user_content=user_content,
            schema=reply_bundle_json_schema(),
            schema_title="reply_bundle",
            provider=self.provider_name,
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            prompt_metadata=identity.tracing_metadata(model=self.model_name),
        )
        bundle = ReplyBundle.model_validate(result["data"])
        if not bundle.dialect_stamp:
            bundle = bundle.model_copy(update={"dialect_stamp": build_dialect_stamp(request.context)})
        prompt_tokens = result.get("prompt_tokens") or 0
        completion_tokens = result.get("completion_tokens") or 0
        await log_llm_usage(
            user_id=get_current_user_id(),
            operation="translate_to_esuy",
            provider=self.provider_name,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=result.get("total_tokens"),
        )
        usage = usage_snapshot(
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=result.get("total_tokens"),
        )
        return bundle, usage

    async def understand_incoming(self, request: UnderstandTextRequest) -> UnderstandTextResponse:
        require_langchain_for_text()
        self.last_usage = None
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await self._understand_incoming_once(request)
            except Exception as error:
                last_error = error
                if attempt == 0:
                    logger.warning("understand_incoming retry after error: %s", error)
                    import asyncio

                    await asyncio.sleep(0.8)
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("understand_incoming failed without error")

    async def _understand_incoming_once(self, request: UnderstandTextRequest) -> UnderstandTextResponse:
        from decime_api.services.ai.lc.structured_chat import ainvoke_structured
        from decime_api.services.analytics.llm_usage import log_llm_usage, usage_snapshot
        from decime_api.services.analytics.request_context import get_current_user_id

        started = time.perf_counter()
        system_prompt, user_content, identity = render_prompt(
            "understand_incoming",
            target_is_ru=request.target_language == "ru",
            payload_json=_understand_payload(request),
        )
        result = await ainvoke_structured(
            operation="understand_incoming",
            system_prompt=system_prompt,
            user_content=user_content,
            schema=understand_text_json_schema(),
            schema_title="understand_text",
            provider=self.provider_name,
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            prompt_metadata=identity.tracing_metadata(model=self.model_name),
        )
        payload = dict(result["data"])
        payload["original_text"] = request.source_text.strip()
        if not isinstance(payload.get("tone_notes_ru"), list):
            payload["tone_notes_ru"] = []
        if not isinstance(payload.get("uncertain_parts"), list):
            payload["uncertain_parts"] = []
        parsed = UnderstandTextResponse.model_validate(payload)
        prompt_tokens = result.get("prompt_tokens") or 0
        completion_tokens = result.get("completion_tokens") or 0
        await log_llm_usage(
            user_id=get_current_user_id(),
            operation="understand_incoming",
            provider=self.provider_name,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=result.get("total_tokens"),
        )
        self.last_usage = usage_snapshot(
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=result.get("total_tokens"),
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "understand_incoming provider=%s model=%s orchestrator=langchain latency_ms=%s",
            self.provider_name,
            self.model_name,
            latency_ms,
        )
        return parsed
