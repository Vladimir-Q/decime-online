"""Dictionary export/import via n8n + Google Sheets."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx

from decime_api.config import settings
from decime_api.db.sheets_jobs import (
    SheetsImportRowRecord,
    SheetsJobRecord,
    SheetsJobRepository,
)
from decime_api.db.training import TrainingItemRecord, TrainingRepository
from decime_api.schemas.training import (
    N8nCompleteJobRequest,
    N8nImportRowRequest,
    N8nImportRowResponse,
    N8nJobContextResponse,
    SheetsExportRequest,
    SheetsImportRequest,
    SheetsJobAcceptedResponse,
    SheetsJobReport,
    SheetsJobStatusResponse,
)
from decime_api.services.ai.training_extractor import TrainingExtractor
from decime_api.services.training.canonical import build_canonical_key

logger = logging.getLogger(__name__)

_SPREADSHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")
_MAX_CELL_CHARS = 2000
AUTOMATION_HEADER = "X-Decime-Automation-Key"


class SheetsConfigError(RuntimeError):
    pass


class SheetsConflictError(RuntimeError):
    pass


class SheetsNotFoundError(RuntimeError):
    pass


class SheetsN8nError(RuntimeError):
    pass


def parse_spreadsheet_id(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError("source_spreadsheet_id is required")
    match = _SPREADSHEET_ID_RE.search(text)
    if match:
        return match.group(1)
    # Bare ID
    if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", text):
        return text
    raise ValueError("Invalid Google Spreadsheet ID or URL")


def sheet_name_for_user(user_id: str) -> str:
    return f"user_{user_id}"


def _report_from_dict(data: dict[str, Any] | None) -> SheetsJobReport:
    return SheetsJobReport.model_validate(data or {})


def job_to_status_response(job: SheetsJobRecord) -> SheetsJobStatusResponse:
    return SheetsJobStatusResponse(
        job_id=job.job_id,
        kind=job.kind,
        status=job.status,
        list_id=job.list_id,
        spreadsheet_id=job.spreadsheet_id,
        sheet_name=job.sheet_name,
        source_spreadsheet_id=job.source_spreadsheet_id,
        source_sheet_name=job.source_sheet_name,
        report=_report_from_dict(job.report),
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


def job_to_n8n_context(job: SheetsJobRecord) -> N8nJobContextResponse:
    return N8nJobContextResponse(
        job_id=job.job_id,
        kind=job.kind,
        status=job.status,
        user_id=job.user_id,
        list_id=job.list_id,
        spreadsheet_id=job.spreadsheet_id,
        sheet_name=job.sheet_name,
        source_spreadsheet_id=job.source_spreadsheet_id,
        source_sheet_name=job.source_sheet_name,
        max_import_rows=settings.dictionary_sheets_max_import_rows,
        report=_report_from_dict(job.report),
    )


async def expire_stale_jobs(jobs: SheetsJobRepository) -> None:
    minutes = max(1, settings.dictionary_sheets_job_timeout_minutes)
    older_than = datetime.now(UTC) - timedelta(minutes=minutes)
    await jobs.mark_timed_out_jobs(older_than=older_than)


def _require_sheets_config(*, kind: str) -> None:
    if not settings.n8n_automation_key:
        raise SheetsConfigError("Dictionary Sheets integration is not configured")
    if kind == "export":
        if not settings.n8n_export_webhook_url:
            raise SheetsConfigError("N8N_EXPORT_WEBHOOK_URL is not configured")
        if not settings.google_dictionary_spreadsheet_id:
            raise SheetsConfigError("GOOGLE_DICTIONARY_SPREADSHEET_ID is not configured")
    elif kind == "import":
        if not settings.n8n_import_webhook_url:
            raise SheetsConfigError("N8N_IMPORT_WEBHOOK_URL is not configured")


def _latin1_header_value(name: str, value: str) -> str:
    """HTTP headers must be Latin-1; reject bad secrets before the request is built."""
    try:
        value.encode("latin-1")
    except UnicodeEncodeError as error:
        raise SheetsN8nError(
            f"{name} contains non-ASCII characters and cannot be sent as an HTTP header"
        ) from error
    return value


async def _mark_job_failed(
    jobs: SheetsJobRepository,
    job_id: str,
    error_message: str,
) -> SheetsJobRecord | None:
    """Move an active job to failed. A job already completed or failed is left as-is."""
    return await jobs.update_job(
        job_id,
        status="failed",
        error_message=error_message,
        finished_at=datetime.now(UTC),
    )


def _accepted_response(job_id: str, job: SheetsJobRecord | None) -> SheetsJobAcceptedResponse:
    status = job.status if job is not None else "running"
    return SheetsJobAcceptedResponse(job_id=job_id, status=status)


async def _post_n8n_webhook(url: str, payload: dict[str, Any]) -> None:
    key = _latin1_header_value(
        "N8N_AUTOMATION_KEY", settings.n8n_automation_key or ""
    )
    headers = {
        AUTOMATION_HEADER: key,
        "Content-Type": "application/json",
    }
    timeout = settings.n8n_webhook_timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
    except SheetsN8nError:
        raise
    except httpx.TimeoutException as error:
        logger.warning("n8n webhook timeout url_host=%s", httpx.URL(url).host)
        raise SheetsN8nError("n8n webhook timed out") from error
    except httpx.HTTPError as error:
        logger.warning("n8n webhook connection error: %s", type(error).__name__)
        raise SheetsN8nError("Could not reach n8n webhook") from error
    except Exception as error:
        # e.g. UnicodeEncodeError while httpx encodes headers, unexpected client bugs
        logger.warning(
            "n8n webhook unexpected error type=%s",
            type(error).__name__,
        )
        raise SheetsN8nError(
            f"n8n webhook failed before/during request ({type(error).__name__})"
        ) from error

    if response.status_code >= 400:
        logger.warning(
            "n8n webhook rejected status=%s",
            response.status_code,
        )
        raise SheetsN8nError(f"n8n webhook rejected the job ({response.status_code})")


async def _assert_list_owner(
    training: TrainingRepository, user_id: str, list_id: str
) -> None:
    try:
        await training.list_items(user_id, list_id)
    except ValueError as error:
        raise SheetsNotFoundError(str(error)) from error


async def start_export(
    user_id: str,
    request: SheetsExportRequest,
    *,
    training: TrainingRepository,
    jobs: SheetsJobRepository,
) -> SheetsJobAcceptedResponse:
    await expire_stale_jobs(jobs)
    _require_sheets_config(kind="export")
    await _assert_list_owner(training, user_id, request.list_id)

    if await jobs.has_active_export(user_id):
        raise SheetsConflictError("An export is already in progress")

    job_id = str(uuid4())
    spreadsheet_id = settings.google_dictionary_spreadsheet_id
    sheet_name = sheet_name_for_user(user_id)
    now = datetime.now(UTC)
    job = SheetsJobRecord(
        job_id=job_id,
        user_id=user_id,
        list_id=request.list_id,
        kind="export",
        status="queued",
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        created_at=now,
        updated_at=now,
    )
    try:
        await jobs.create_job(job)
    except ValueError as error:
        raise SheetsConflictError(str(error)) from error

    payload = {
        "job_id": job_id,
        "user_id": user_id,
        "list_id": request.list_id,
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
    }
    try:
        await _post_n8n_webhook(settings.n8n_export_webhook_url or "", payload)
    except SheetsN8nError as error:
        current = await _mark_job_failed(jobs, job_id, str(error))
        if current is not None and current.status == "completed":
            return _accepted_response(job_id, current)
        raise
    except Exception as error:
        message = f"n8n webhook failed ({type(error).__name__})"
        logger.exception("start_export webhook unexpected error job_id=%s", job_id)
        current = await _mark_job_failed(jobs, job_id, message)
        if current is not None and current.status == "completed":
            return _accepted_response(job_id, current)
        raise SheetsN8nError(message) from error

    updated = await jobs.update_job(
        job_id,
        status="running",
        accepted_at=datetime.now(UTC),
    )
    return _accepted_response(job_id, updated)


async def start_import(
    user_id: str,
    request: SheetsImportRequest,
    *,
    training: TrainingRepository,
    jobs: SheetsJobRepository,
) -> SheetsJobAcceptedResponse:
    await expire_stale_jobs(jobs)
    _require_sheets_config(kind="import")
    await _assert_list_owner(training, user_id, request.list_id)

    try:
        source_spreadsheet_id = parse_spreadsheet_id(request.source_spreadsheet_id)
    except ValueError as error:
        raise SheetsConfigError(str(error)) from error
    source_sheet_name = request.source_sheet_name.strip()
    if not source_sheet_name:
        raise SheetsConfigError("source_sheet_name is required")

    job_id = str(uuid4())
    now = datetime.now(UTC)
    job = SheetsJobRecord(
        job_id=job_id,
        user_id=user_id,
        list_id=request.list_id,
        kind="import",
        status="queued",
        source_spreadsheet_id=source_spreadsheet_id,
        source_sheet_name=source_sheet_name,
        created_at=now,
        updated_at=now,
    )
    await jobs.create_job(job)

    payload = {
        "job_id": job_id,
        "source_spreadsheet_id": source_spreadsheet_id,
        "source_sheet_name": source_sheet_name,
    }
    try:
        await _post_n8n_webhook(settings.n8n_import_webhook_url or "", payload)
    except SheetsN8nError as error:
        current = await _mark_job_failed(jobs, job_id, str(error))
        if current is not None and current.status == "completed":
            return _accepted_response(job_id, current)
        raise
    except Exception as error:
        message = f"n8n webhook failed ({type(error).__name__})"
        logger.exception("start_import webhook unexpected error job_id=%s", job_id)
        current = await _mark_job_failed(jobs, job_id, message)
        if current is not None and current.status == "completed":
            return _accepted_response(job_id, current)
        raise SheetsN8nError(message) from error

    updated = await jobs.update_job(
        job_id,
        status="running",
        accepted_at=datetime.now(UTC),
    )
    return _accepted_response(job_id, updated)


async def get_job_for_user(
    user_id: str,
    job_id: str,
    *,
    jobs: SheetsJobRepository,
) -> SheetsJobStatusResponse:
    await expire_stale_jobs(jobs)
    job = await jobs.get_job_for_user(job_id, user_id)
    if job is None:
        raise SheetsNotFoundError("Job not found")
    return job_to_status_response(job)


async def get_job_for_n8n(
    job_id: str,
    *,
    jobs: SheetsJobRepository,
) -> N8nJobContextResponse:
    await expire_stale_jobs(jobs)
    job = await jobs.get_job(job_id)
    if job is None:
        raise SheetsNotFoundError("Job not found")
    return job_to_n8n_context(job)


async def import_row(
    job_id: str,
    request: N8nImportRowRequest,
    *,
    training: TrainingRepository,
    jobs: SheetsJobRepository,
    extractor: TrainingExtractor,
) -> N8nImportRowResponse:
    await expire_stale_jobs(jobs)
    job = await jobs.get_job(job_id)
    if job is None:
        raise SheetsNotFoundError("Job not found")
    if job.kind != "import":
        raise SheetsConfigError("Job is not an import job")
    if job.status in ("completed", "failed"):
        raise SheetsConflictError("Job is already finished")
    if job.status == "queued":
        updated = await jobs.update_job(job_id, status="running")
        if updated is None or updated.status in ("completed", "failed"):
            raise SheetsConflictError("Job is already finished")

    existing = await jobs.get_import_row(job_id, request.source_row_number)
    if existing is not None:
        return N8nImportRowResponse(
            status=existing.status,
            item_id=existing.item_id,
            message=existing.message,
        )

    counts = await jobs.count_import_rows(job_id)
    processed = sum(counts.values())
    if processed >= settings.dictionary_sheets_max_import_rows:
        result = N8nImportRowResponse(
            status="error",
            message="Import row limit exceeded",
        )
        await jobs.save_import_row(
            SheetsImportRowRecord(
                job_id=job_id,
                source_row_number=request.source_row_number,
                status="error",
                message=result.message,
            )
        )
        return result

    spanish = (request.spanish or "").strip()
    russian = (request.russian or "").strip()
    if not spanish:
        result = N8nImportRowResponse(status="error", message="Empty spanish cell")
        await jobs.save_import_row(
            SheetsImportRowRecord(
                job_id=job_id,
                source_row_number=request.source_row_number,
                status="error",
                message=result.message,
            )
        )
        return result
    if len(spanish) > _MAX_CELL_CHARS or len(russian) > _MAX_CELL_CHARS:
        result = N8nImportRowResponse(status="error", message="Cell text too long")
        await jobs.save_import_row(
            SheetsImportRowRecord(
                job_id=job_id,
                source_row_number=request.source_row_number,
                status="error",
                message=result.message,
            )
        )
        return result

    try:
        candidate = await extractor.normalize_dictionary_row(
            spanish=spanish,
            russian=russian or None,
            target_locale="es-UY-montevideo",
        )
    except Exception as error:  # noqa: BLE001 — one failed row must not abort the import
        logger.warning("normalize_dictionary_row failed: %s", type(error).__name__)
        result = N8nImportRowResponse(
            status="error",
            message="AI normalization failed",
        )
        await jobs.save_import_row(
            SheetsImportRowRecord(
                job_id=job_id,
                source_row_number=request.source_row_number,
                status="error",
                message=result.message,
            )
        )
        return result

    canonical = build_canonical_key(
        item_type=candidate.item_type,
        surface_text=candidate.surface_text,
        lemma=candidate.lemma,
        grammar=candidate.grammar,
    )
    # Uniqueness is per user globally.
    known = await training.get_known_canonical_keys(job.user_id, list_id=None)
    if canonical in known:
        result = N8nImportRowResponse(
            status="skipped_duplicate",
            message="Duplicate canonical_key",
        )
        await jobs.save_import_row(
            SheetsImportRowRecord(
                job_id=job_id,
                source_row_number=request.source_row_number,
                status="skipped_duplicate",
                message=result.message,
            )
        )
        return result

    item_id = str(uuid4())
    item = TrainingItemRecord(
        item_id=item_id,
        list_id=job.list_id,
        candidate=candidate.model_copy(update={"canonical_key": canonical}),
        canonical_key=canonical,
        review_stage=0,
        next_review_at=datetime.now(UTC),
    )
    try:
        await training.add_items(job.user_id, [item])
    except Exception as error:
        # Concurrent insert against unique (user_id, canonical_key).
        err_name = type(error).__name__
        err_text = str(error).lower()
        if "unique" in err_name.lower() or "unique" in err_text or "duplicate" in err_text:
            result = N8nImportRowResponse(
                status="skipped_duplicate",
                message="Duplicate canonical_key",
            )
            await jobs.save_import_row(
                SheetsImportRowRecord(
                    job_id=job_id,
                    source_row_number=request.source_row_number,
                    status="skipped_duplicate",
                    message=result.message,
                )
            )
            return result
        logger.exception("import_row insert failed")
        result = N8nImportRowResponse(status="error", message="Failed to save card")
        await jobs.save_import_row(
            SheetsImportRowRecord(
                job_id=job_id,
                source_row_number=request.source_row_number,
                status="error",
                message=result.message,
            )
        )
        return result

    result = N8nImportRowResponse(status="created", item_id=item_id)
    await jobs.save_import_row(
        SheetsImportRowRecord(
            job_id=job_id,
            source_row_number=request.source_row_number,
            status="created",
            item_id=item_id,
        )
    )
    return result


async def complete_job(
    job_id: str,
    request: N8nCompleteJobRequest,
    *,
    jobs: SheetsJobRepository,
) -> SheetsJobStatusResponse:
    await expire_stale_jobs(jobs)
    job = await jobs.get_job(job_id)
    if job is None:
        raise SheetsNotFoundError("Job not found")

    # Terminal states are protected from late callbacks.
    if job.status in ("completed", "failed"):
        return job_to_status_response(job)

    report = request.report.model_dump()
    if job.kind == "import":
        counts = await jobs.count_import_rows(job_id)
        report["created"] = counts.get("created", 0)
        report["skipped"] = counts.get("skipped_duplicate", 0)
        report["errors"] = counts.get("error", 0)
        report["partial"] = bool(report.get("errors")) or bool(request.report.partial)
        if request.status == "completed" and not any(counts.values()) and not request.report.message:
            # Empty import is valid (no data rows).
            report.setdefault("message", "No rows imported")

    status = request.status
    error_message = request.error_message
    if status == "failed" and not error_message:
        error_message = request.report.message or "n8n reported failure"

    updated = await jobs.update_job(
        job_id,
        status=status,
        report=report,
        error_message=error_message,
        finished_at=datetime.now(UTC),
    )
    if updated is None:
        raise SheetsNotFoundError("Job not found")
    return job_to_status_response(updated)
