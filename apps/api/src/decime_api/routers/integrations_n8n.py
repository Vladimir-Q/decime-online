from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from decime_api.auth.dependencies import require_n8n_automation
from decime_api.db.sheets_jobs import SheetsJobRepository, get_sheets_job_repository
from decime_api.db.training import TrainingRepository, get_training_repository
from decime_api.dependencies import get_training_extractor
from decime_api.schemas.training import (
    N8nCompleteJobRequest,
    N8nImportRowRequest,
    N8nImportRowResponse,
    N8nJobContextResponse,
    SheetsJobStatusResponse,
)
from decime_api.services.ai.training_extractor import TrainingExtractor
from decime_api.services.training.sheets_service import (
    SheetsConfigError,
    SheetsConflictError,
    SheetsNotFoundError,
    complete_job,
    get_job_for_n8n,
    import_row,
)

router = APIRouter(
    prefix="/integrations/n8n",
    tags=["integrations-n8n"],
    dependencies=[Depends(require_n8n_automation)],
)


@router.get("/jobs/{job_id}", response_model=N8nJobContextResponse)
async def n8n_get_job(
    job_id: str,
    jobs: Annotated[SheetsJobRepository, Depends(get_sheets_job_repository)],
) -> N8nJobContextResponse:
    try:
        return await get_job_for_n8n(job_id, jobs=jobs)
    except SheetsNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/jobs/{job_id}/import-row", response_model=N8nImportRowResponse)
async def n8n_import_row(
    job_id: str,
    request: N8nImportRowRequest,
    jobs: Annotated[SheetsJobRepository, Depends(get_sheets_job_repository)],
    training: Annotated[TrainingRepository, Depends(get_training_repository)],
    extractor: Annotated[TrainingExtractor, Depends(get_training_extractor)],
) -> N8nImportRowResponse:
    try:
        return await import_row(
            job_id,
            request,
            training=training,
            jobs=jobs,
            extractor=extractor,
        )
    except SheetsNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SheetsConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SheetsConfigError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/jobs/{job_id}/complete", response_model=SheetsJobStatusResponse)
async def n8n_complete_job(
    job_id: str,
    request: N8nCompleteJobRequest,
    jobs: Annotated[SheetsJobRepository, Depends(get_sheets_job_repository)],
) -> SheetsJobStatusResponse:
    try:
        return await complete_job(job_id, request, jobs=jobs)
    except SheetsNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
