import json
import logging
import time
from pathlib import Path

from decime_api.schemas.training import ExtractCandidatesRequest, TrainingCandidate
from decime_api.services.ai.extraction_parse import parse_extraction_bundle
from decime_api.services.ai.lc.orchestrator import require_langchain_for_text
from decime_api.services.ai.lc.prompt_provider import render_prompt
from decime_api.services.ai.llm_json_schemas import (
    extraction_bundle_json_schema,
    normalize_dictionary_item_json_schema,
)
from decime_api.services.ai.normalize_parse import parse_normalized_candidate

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "extract_training_items.md"
NORMALIZE_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "normalize_dictionary_item.md"
)


def _extract_user_content(request: ExtractCandidatesRequest) -> str:
    _system, human, _identity = render_prompt(
        "extract_candidates",
        payload_json=json.dumps(request.model_dump(), ensure_ascii=False, indent=2),
    )
    return human


def _normalize_user_content(*, spanish: str, russian: str | None, target_locale: str) -> str:
    payload = {
        "spanish": spanish,
        "russian": russian or "",
        "target_locale": target_locale,
    }
    _system, human, _identity = render_prompt(
        "normalize_dictionary_row",
        payload_json=json.dumps(payload, ensure_ascii=False, indent=2),
    )
    return human


class OpenAITrainingExtractor:
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

    async def extract_candidates(self, request: ExtractCandidatesRequest):
        require_langchain_for_text()
        started = time.perf_counter()
        system_prompt, user_content, identity = render_prompt(
            "extract_candidates",
            payload_json=json.dumps(request.model_dump(), ensure_ascii=False, indent=2),
        )
        raw = await self._structured_json(
            operation="extract_candidates",
            system_prompt=system_prompt,
            user_content=user_content,
            schema=extraction_bundle_json_schema(),
            schema_title="extraction_bundle",
            prompt_metadata=identity.tracing_metadata(model=self.model_name),
        )
        bundle = parse_extraction_bundle(raw, request)
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "extract_candidates provider=%s model=%s orchestrator=langchain count=%s latency_ms=%s",
            self.provider_name,
            self.model_name,
            len(bundle.candidates),
            latency_ms,
        )
        return bundle

    async def normalize_dictionary_row(
        self,
        *,
        spanish: str,
        russian: str | None = None,
        target_locale: str = "es-UY-montevideo",
    ) -> TrainingCandidate:
        require_langchain_for_text()
        started = time.perf_counter()
        payload = {
            "spanish": spanish,
            "russian": russian or "",
            "target_locale": target_locale,
        }
        system_prompt, user_content, identity = render_prompt(
            "normalize_dictionary_row",
            payload_json=json.dumps(payload, ensure_ascii=False, indent=2),
        )
        raw = await self._structured_json(
            operation="normalize_dictionary_row",
            system_prompt=system_prompt,
            user_content=user_content,
            schema=normalize_dictionary_item_json_schema(),
            schema_title="normalize_dictionary_item",
            prompt_metadata=identity.tracing_metadata(model=self.model_name),
        )
        candidate = parse_normalized_candidate(
            raw,
            spanish=spanish,
            russian=russian,
            target_locale=target_locale,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "normalize_dictionary_row provider=%s model=%s orchestrator=langchain latency_ms=%s",
            self.provider_name,
            self.model_name,
            latency_ms,
        )
        return candidate

    async def _structured_json(
        self,
        *,
        operation: str,
        system_prompt: str,
        user_content: str,
        schema: dict,
        schema_title: str,
        prompt_metadata: dict | None = None,
    ) -> dict:
        from decime_api.services.ai.lc.structured_chat import ainvoke_structured

        result = await ainvoke_structured(
            operation=operation,  # type: ignore[arg-type]
            system_prompt=system_prompt,
            user_content=user_content,
            schema=schema,
            schema_title=schema_title,
            provider=self.provider_name,
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            prompt_metadata=prompt_metadata,
        )
        return dict(result["data"])
