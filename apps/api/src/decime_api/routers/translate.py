from typing import Annotated

from fastapi import APIRouter, Depends

from decime_api.auth.dependencies import CurrentUser, get_current_user
from decime_api.auth.user_scope import resolve_user_id
from decime_api.dependencies import get_history_repository, get_llm_provider
from decime_api.schemas.compose import TranslateToEsRequest, TranslateToEsResponse
from decime_api.services.ai.llm_provider import LLMProvider
from decime_api.services.compose.reply_composer import HistoryRepository, translate_to_esuy
from decime_api.services.http_errors import raise_upstream_error

router = APIRouter(prefix="/translate", tags=["translate"])


@router.post("/text", response_model=TranslateToEsResponse)
async def translate_to_esuy_endpoint(
    request: TranslateToEsRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    llm: LLMProvider = Depends(get_llm_provider),
    history: HistoryRepository = Depends(get_history_repository),
) -> TranslateToEsResponse:
    """Translate RU/EN (or auto) draft into Uruguayan Spanish. Translation only."""
    user_id = resolve_user_id(user)
    try:
        return await translate_to_esuy(user_id, request, llm, history)
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        from decime_api.services.analytics.event_log import EVENT_ERROR_OCCURRED, log_event

        await log_event(user_id, EVENT_ERROR_OCCURRED, {"route": "translate/text", "error": str(error)})
        raise_upstream_error("translate/text", error)
