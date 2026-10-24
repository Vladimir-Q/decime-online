from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from decime_api.auth.dependencies import CurrentUser, get_current_user, require_authenticated_user
from decime_api.auth.user_scope import resolve_user_id
from decime_api.db.sheets_jobs import SheetsJobRepository, get_sheets_job_repository
from decime_api.db.training import TrainingRepository, get_training_repository
from decime_api.dependencies import get_audio_storage, get_training_extractor, get_tts_provider
from decime_api.schemas.training import (
    AddToVocabRequest,
    AddToVocabResponse,
    ApproveCandidatesRequest,
    ApproveCandidatesResponse,
    ExtractCandidatesRequest,
    ExtractCandidatesResponse,
    ItemAudioResponse,
    ReviewNextResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    SheetsExportRequest,
    SheetsImportRequest,
    SheetsJobAcceptedResponse,
    SheetsJobStatusResponse,
    TrainingItemsResponse,
    TrainingItemSummary,
    TrainingListSummary,
)
from decime_api.services.ai.training_extractor import TrainingExtractor
from decime_api.services.http_errors import raise_upstream_error
from decime_api.services.storage.audio_storage import LocalAudioStorage
from decime_api.services.training.review import get_review_next, submit_review
from decime_api.services.training.sheets_service import (
    SheetsConfigError,
    SheetsConflictError,
    SheetsN8nError,
    SheetsNotFoundError,
    get_job_for_user,
    start_export,
    start_import,
)
from decime_api.services.training.training_service import (
    add_spanish_to_vocab,
    approve_training_candidates,
    delete_training_item,
    extract_training_candidates,
    generate_item_audio,
    list_training_lists,
)

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/extract-candidates", response_model=ExtractCandidatesResponse)
async def extract_candidates(
    request: ExtractCandidatesRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    extractor: TrainingExtractor = Depends(get_training_extractor),
    repository: TrainingRepository = Depends(get_training_repository),
) -> ExtractCandidatesResponse:
    user_id = resolve_user_id(user)
    if not request.list_id:
        request = request.model_copy(update={"list_id": repository.get_default_list_id(user_id)})
    try:
        return await extract_training_candidates(
            user_id, request, extractor=extractor, repository=repository
        )
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        raise_upstream_error("training/extract-candidates", error)


@router.post("/approve-candidates", response_model=ApproveCandidatesResponse)
async def approve_candidates(
    request: ApproveCandidatesRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    repository: TrainingRepository = Depends(get_training_repository),
    tts=Depends(get_tts_provider),
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> ApproveCandidatesResponse:
    user_id = resolve_user_id(user)
    try:
        return await approve_training_candidates(
            user_id, request, repository=repository, tts=tts, storage=storage
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        raise_upstream_error("training/approve-candidates", error)


@router.post("/add-to-vocab", response_model=AddToVocabResponse)
async def add_to_vocab(
    request: AddToVocabRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    extractor: TrainingExtractor = Depends(get_training_extractor),
    repository: TrainingRepository = Depends(get_training_repository),
    tts=Depends(get_tts_provider),
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> AddToVocabResponse:
    user_id = resolve_user_id(user)
    try:
        return await add_spanish_to_vocab(
            user_id,
            request,
            extractor=extractor,
            repository=repository,
            tts=tts,
            storage=storage,
        )
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        raise_upstream_error("training/add-to-vocab", error)


@router.get("/lists", response_model=list[TrainingListSummary])
async def get_lists(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    repository: TrainingRepository = Depends(get_training_repository),
) -> list[TrainingListSummary]:
    user_id = resolve_user_id(user)
    return await list_training_lists(user_id, repository)


@router.get("/items", response_model=TrainingItemsResponse)
async def get_items(
    list_id: str = Query(...),
    user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    repository: TrainingRepository = Depends(get_training_repository),
) -> TrainingItemsResponse:
    user_id = resolve_user_id(user)
    try:
        records = await repository.list_items(user_id, list_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    items = [
        TrainingItemSummary(
            item_id=record.item_id,
            list_id=record.list_id,
            item_type=record.candidate.item_type,
            display_text=record.candidate.display_text,
            translations_ru=record.candidate.translations_ru,
            translations_en=record.candidate.translations_en,
            example_es=record.candidate.example_es,
            audio_id=record.audio_id,
            audio_status=record.audio_status,
            review_stage=record.review_stage,
            next_review_at=record.next_review_at.isoformat(),
            created_at=record.created_at.isoformat(),
        )
        for record in sorted(records, key=lambda item: item.created_at, reverse=True)
    ]
    return TrainingItemsResponse(items=items)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    repository: TrainingRepository = Depends(get_training_repository),
) -> None:
    user_id = resolve_user_id(user)
    deleted = await delete_training_item(user_id, item_id, repository=repository)
    if not deleted:
        raise HTTPException(status_code=404, detail="Training item not found")


@router.post("/items/{item_id}/audio", response_model=ItemAudioResponse)
async def create_item_audio(
    item_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    repository: TrainingRepository = Depends(get_training_repository),
    tts=Depends(get_tts_provider),
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> ItemAudioResponse:
    user_id = resolve_user_id(user)
    try:
        return await generate_item_audio(
            user_id,
            item_id,
            repository=repository,
            tts=tts,
            storage=storage,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        raise_upstream_error("training/items/audio", error)


@router.get("/review/next", response_model=ReviewNextResponse)
async def review_next(
    list_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=50),
    user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    repository: TrainingRepository = Depends(get_training_repository),
) -> ReviewNextResponse:
    user_id = resolve_user_id(user)
    try:
        return await get_review_next(
            user_id=user_id, list_id=list_id, limit=limit, repository=repository
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/review/submit", response_model=ReviewSubmitResponse)
async def review_submit(
    request: ReviewSubmitRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    repository: TrainingRepository = Depends(get_training_repository),
) -> ReviewSubmitResponse:
    user_id = resolve_user_id(user)
    try:
        return await submit_review(user_id, request, repository=repository)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/sheets/export",
    response_model=SheetsJobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sheets_export(
    request: SheetsExportRequest,
    response: Response,
    user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    repository: TrainingRepository = Depends(get_training_repository),
    jobs: SheetsJobRepository = Depends(get_sheets_job_repository),
) -> SheetsJobAcceptedResponse:
    assert user.id is not None
    try:
        result = await start_export(
            user.id, request, training=repository, jobs=jobs
        )
    except SheetsNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SheetsConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SheetsConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SheetsN8nError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.post(
    "/sheets/import",
    response_model=SheetsJobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sheets_import(
    request: SheetsImportRequest,
    response: Response,
    user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    repository: TrainingRepository = Depends(get_training_repository),
    jobs: SheetsJobRepository = Depends(get_sheets_job_repository),
) -> SheetsJobAcceptedResponse:
    assert user.id is not None
    try:
        result = await start_import(
            user.id, request, training=repository, jobs=jobs
        )
    except SheetsNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SheetsConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SheetsConfigError as error:
        # Invalid spreadsheet id/name → 400; missing server config → 503
        detail = str(error)
        code = 503 if "not configured" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail) from error
    except SheetsN8nError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.get("/sheets/jobs/{job_id}", response_model=SheetsJobStatusResponse)
async def sheets_job_status(
    job_id: str,
    user: Annotated[CurrentUser, Depends(require_authenticated_user)],
    jobs: SheetsJobRepository = Depends(get_sheets_job_repository),
) -> SheetsJobStatusResponse:
    assert user.id is not None
    try:
        return await get_job_for_user(user.id, job_id, jobs=jobs)
    except SheetsNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
