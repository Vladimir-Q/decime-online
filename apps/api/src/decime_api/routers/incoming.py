from typing import Annotated

from fastapi import APIRouter, Depends

from decime_api.auth.dependencies import CurrentUser, get_current_user
from decime_api.auth.user_scope import resolve_user_id
from decime_api.dependencies import get_llm_provider
from decime_api.schemas.incoming import UnderstandTextRequest, UnderstandTextResponse
from decime_api.services.ai.llm_provider import LLMProvider
from decime_api.services.http_errors import raise_upstream_error

router = APIRouter(prefix="/incoming", tags=["incoming"])


@router.post("/understand-text", response_model=UnderstandTextResponse)
async def understand_text(
    request: UnderstandTextRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    llm: LLMProvider = Depends(get_llm_provider),
) -> UnderstandTextResponse:
    user_id = resolve_user_id(user)
    try:
        return await llm.understand_incoming(request)
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        from decime_api.services.analytics.event_log import EVENT_ERROR_OCCURRED, log_event

        await log_event(user_id, EVENT_ERROR_OCCURRED, {"route": "incoming/understand-text", "error": str(error)})
        raise_upstream_error("incoming/understand-text", error)
