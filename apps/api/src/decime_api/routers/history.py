from typing import Annotated

from fastapi import APIRouter, Depends, Query

from decime_api.auth.dependencies import CurrentUser, get_current_user
from decime_api.auth.user_scope import resolve_user_id
from decime_api.db.training import get_training_repository
from decime_api.dependencies import get_audio_storage, get_history_repository
from decime_api.schemas.history import HistoryListResponse
from decime_api.services.audio.audio_service import clear_user_audio_data
from decime_api.services.compose.reply_composer import HistoryRepository
from decime_api.services.storage.audio_storage import LocalAudioStorage

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    history: HistoryRepository = Depends(get_history_repository),
) -> HistoryListResponse:
    user_id = resolve_user_id(user)
    return await history.list_history(user_id, limit=limit)


@router.delete("")
async def clear_history(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    history: HistoryRepository = Depends(get_history_repository),
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> dict[str, str]:
    user_id = resolve_user_id(user)
    await history.clear(user_id)
    clear_user_audio_data(storage, user_id)
    training_repo = get_training_repository()
    await training_repo.clear(user_id)
    return {"status": "ok", "message": "History, training data, and audio cache cleared for user"}
