import logging
import time
from typing import Any, Protocol
from uuid import uuid4

from decime_api.schemas.compose import ReplyBundle, TranslateToEsRequest, TranslateToEsResponse
from decime_api.schemas.history import HistoryItem, HistoryListResponse
from decime_api.services.ai.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class HistoryRepository(Protocol):
    async def save_request(self, user_id: str, request: TranslateToEsRequest) -> str: ...

    async def save_output(
        self,
        user_id: str,
        request_id: str,
        bundle: ReplyBundle,
        *,
        provider: str,
        model: str,
        latency_ms: int,
    ) -> None: ...

    async def list_history(self, user_id: str, *, limit: int = 20) -> HistoryListResponse: ...

    async def clear(self, user_id: str) -> None: ...


class MemoryHistoryRepository:
    def __init__(self) -> None:
        self._requests: dict[str, dict[str, Any]] = {}
        self._outputs: dict[str, dict[str, Any]] = {}
        self._owners: dict[str, str] = {}

    async def save_request(self, user_id: str, request: TranslateToEsRequest) -> str:
        request_id = str(uuid4())
        self._requests[request_id] = {
            "request_id": request_id,
            "source_language": request.source_language,
            "source_text": request.source_text,
            "incoming_text": None,
            "channel": request.context.channel,
            "tone": None,
            "situation": None,
            "target_locale": request.context.target_locale,
            "user_level": request.context.user_level,
            "created_at": _utc_now_iso(),
        }
        self._owners[request_id] = user_id
        return request_id

    async def save_output(
        self,
        user_id: str,
        request_id: str,
        bundle: ReplyBundle,
        *,
        provider: str,
        model: str,
        latency_ms: int,
    ) -> None:
        if self._owners.get(request_id) != user_id:
            raise ValueError("Reply request not found")
        self._outputs[request_id] = {
            **bundle.model_dump(),
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
        }

    async def list_history(self, user_id: str, *, limit: int = 20) -> HistoryListResponse:
        items: list[HistoryItem] = []
        for request_id, req in sorted(
            self._requests.items(),
            key=lambda pair: pair[1]["created_at"],
            reverse=True,
        ):
            if self._owners.get(request_id) != user_id:
                continue
            output = self._outputs.get(request_id)
            if not output:
                continue
            items.append(
                HistoryItem(
                    request_id=request_id,
                    created_at=req["created_at"],
                    source_language=req["source_language"],
                    source_text=req["source_text"],
                    incoming_text=req["incoming_text"],
                    channel=req["channel"],
                    tone=req["tone"],
                    situation=req["situation"],
                    recommended_reply=output["recommended_reply"],
                    dialect_stamp=output.get("dialect_stamp"),
                    provider=output.get("provider"),
                    model=output.get("model"),
                )
            )
            if len(items) >= limit:
                break
        return HistoryListResponse(items=items, total=len(items))

    async def clear(self, user_id: str) -> None:
        to_delete = [rid for rid, owner in self._owners.items() if owner == user_id]
        for request_id in to_delete:
            self._requests.pop(request_id, None)
            self._outputs.pop(request_id, None)
            self._owners.pop(request_id, None)


async def translate_to_esuy(
    user_id: str,
    request: TranslateToEsRequest,
    llm: LLMProvider,
    history: HistoryRepository,
) -> TranslateToEsResponse:
    started = time.perf_counter()
    request_id = await history.save_request(user_id, request)
    bundle = await llm.translate_to_esuy(request)
    if not bundle.can_add_to_training:
        bundle = bundle.model_copy(update={"can_add_to_training": True})
    latency_ms = int((time.perf_counter() - started) * 1000)
    await history.save_output(
        user_id,
        request_id,
        bundle,
        provider=llm.provider_name,
        model=llm.model_name,
        latency_ms=latency_ms,
    )
    from decime_api.services.analytics.event_log import EVENT_REPLY_GENERATED, log_event

    await log_event(user_id, EVENT_REPLY_GENERATED, {"request_id": request_id})
    logger.info(
        "translate_to_esuy saved request_id=%s provider=%s model=%s latency_ms=%s",
        request_id,
        llm.provider_name,
        llm.model_name,
        latency_ms,
    )
    return TranslateToEsResponse(request_id=request_id, **bundle.model_dump())


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
