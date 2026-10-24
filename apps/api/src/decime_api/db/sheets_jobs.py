"""Persisted dictionary sheets jobs (memory + postgres)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from decime_api.config import settings
from decime_api.schemas.training import (
    SheetsImportRowStatus,
    SheetsJobKind,
    SheetsJobStatus,
)


@dataclass
class SheetsJobRecord:
    job_id: str
    user_id: str
    list_id: str
    kind: SheetsJobKind
    status: SheetsJobStatus
    spreadsheet_id: str | None = None
    sheet_name: str | None = None
    source_spreadsheet_id: str | None = None
    source_sheet_name: str | None = None
    report: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    accepted_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SheetsImportRowRecord:
    job_id: str
    source_row_number: int
    status: SheetsImportRowStatus
    item_id: str | None = None
    message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SheetsJobRepository(Protocol):
    async def create_job(self, job: SheetsJobRecord) -> SheetsJobRecord: ...

    async def get_job(self, job_id: str) -> SheetsJobRecord | None: ...

    async def get_job_for_user(self, job_id: str, user_id: str) -> SheetsJobRecord | None: ...

    async def has_active_export(self, user_id: str) -> bool: ...

    async def update_job(
        self,
        job_id: str,
        *,
        status: SheetsJobStatus | None = None,
        report: dict[str, Any] | None = None,
        error_message: str | None | object = ...,
        accepted_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> SheetsJobRecord | None: ...

    async def mark_timed_out_jobs(self, *, older_than: datetime) -> int: ...

    async def get_import_row(
        self, job_id: str, source_row_number: int
    ) -> SheetsImportRowRecord | None: ...

    async def save_import_row(self, row: SheetsImportRowRecord) -> SheetsImportRowRecord: ...

    async def count_import_rows(self, job_id: str) -> dict[str, int]: ...


_MISSING = object()

# Active → active/terminal only. A terminal status is sticky: the first
# completed/failed write wins, including when a callback races the webhook.
_ACTIVE_STATUSES = ("queued", "running")

# Previous status is checked in the same statement as the write. PostgreSQL
# re-evaluates WHERE after taking the row lock, so a callback that already
# committed ``completed`` cannot be overwritten by a later ``running`` update.
JOB_STATUS_UPDATE_SQL = """
UPDATE dictionary_sheets_jobs
SET status = %s, report = %s::jsonb, error_message = %s,
    accepted_at = %s, finished_at = %s, updated_at = %s
WHERE id = %s AND status = ANY(%s)
RETURNING *
"""


def allowed_previous_statuses(target: str) -> tuple[str, ...]:
    """Statuses from which ``target`` may be written. Empty means never."""
    if target == "running":
        return _ACTIVE_STATUSES
    if target in ("completed", "failed"):
        return _ACTIVE_STATUSES
    return ()


def _apply_transition(
    job: SheetsJobRecord,
    *,
    status: SheetsJobStatus | None,
    report: dict[str, Any] | None,
    error_message: str | None | object,
    accepted_at: datetime | None,
    finished_at: datetime | None,
) -> SheetsJobRecord:
    """Apply a status change only when the current status allows it.

    A rejected transition returns the same record and does not touch report,
    error_message, or finished_at. That is what makes a repeated callback and
    a late ``running`` write idempotent.
    """
    if job.status in ("completed", "failed"):
        return job
    if status is not None and job.status not in allowed_previous_statuses(status):
        return job
    if status is None and job.status not in _ACTIVE_STATUSES:
        return job
    if status is not None:
        job.status = status
    if report is not None:
        job.report = report
    if error_message is not _MISSING:
        job.error_message = error_message  # type: ignore[assignment]
    if accepted_at is not None:
        job.accepted_at = accepted_at
    if finished_at is not None:
        job.finished_at = finished_at
    job.updated_at = datetime.now(UTC)
    return job


class MemorySheetsJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, SheetsJobRecord] = {}
        self._rows: dict[tuple[str, int], SheetsImportRowRecord] = {}

    async def create_job(self, job: SheetsJobRecord) -> SheetsJobRecord:
        if job.kind == "export" and await self.has_active_export(job.user_id):
            raise ValueError("An export is already in progress for this user")
        self._jobs[job.job_id] = job
        return job

    async def get_job(self, job_id: str) -> SheetsJobRecord | None:
        return self._jobs.get(job_id)

    async def get_job_for_user(self, job_id: str, user_id: str) -> SheetsJobRecord | None:
        job = self._jobs.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    async def has_active_export(self, user_id: str) -> bool:
        return any(
            job.user_id == user_id
            and job.kind == "export"
            and job.status in ("queued", "running")
            for job in self._jobs.values()
        )

    async def update_job(
        self,
        job_id: str,
        *,
        status: SheetsJobStatus | None = None,
        report: dict[str, Any] | None = None,
        error_message: str | None | object = _MISSING,
        accepted_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> SheetsJobRecord | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return _apply_transition(
            job,
            status=status,
            report=report,
            error_message=error_message,
            accepted_at=accepted_at,
            finished_at=finished_at,
        )

    async def mark_timed_out_jobs(self, *, older_than: datetime) -> int:
        count = 0
        for job in self._jobs.values():
            if job.status in ("queued", "running") and job.updated_at < older_than:
                job.status = "failed"
                job.error_message = "Job timed out waiting for n8n workflow"
                job.finished_at = datetime.now(UTC)
                job.updated_at = job.finished_at
                count += 1
        return count

    async def get_import_row(
        self, job_id: str, source_row_number: int
    ) -> SheetsImportRowRecord | None:
        return self._rows.get((job_id, source_row_number))

    async def save_import_row(self, row: SheetsImportRowRecord) -> SheetsImportRowRecord:
        key = (row.job_id, row.source_row_number)
        existing = self._rows.get(key)
        if existing is not None:
            return existing
        self._rows[key] = row
        return row

    async def count_import_rows(self, job_id: str) -> dict[str, int]:
        counts = {"created": 0, "skipped_duplicate": 0, "error": 0}
        for (jid, _), row in self._rows.items():
            if jid == job_id and row.status in counts:
                counts[row.status] += 1
        return counts


class PostgresSheetsJobRepository:
    async def create_job(self, job: SheetsJobRecord) -> SheetsJobRecord:
        import json

        from decime_api.db.postgres import postgres_cursor

        with postgres_cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO dictionary_sheets_jobs (
                        id, user_id, list_id, kind, status,
                        spreadsheet_id, sheet_name,
                        source_spreadsheet_id, source_sheet_name,
                        report, error_message, accepted_at, finished_at,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        job.job_id,
                        job.user_id,
                        job.list_id,
                        job.kind,
                        job.status,
                        job.spreadsheet_id,
                        job.sheet_name,
                        job.source_spreadsheet_id,
                        job.source_sheet_name,
                        json.dumps(job.report),
                        job.error_message,
                        job.accepted_at,
                        job.finished_at,
                        job.created_at,
                        job.updated_at,
                    ),
                )
            except Exception as error:
                # Unique active-export index
                if "dictionary_sheets_jobs_one_active_export_idx" in str(error):
                    raise ValueError("An export is already in progress for this user") from error
                raise
        return job

    async def get_job(self, job_id: str) -> SheetsJobRecord | None:
        from decime_api.db.postgres import postgres_cursor

        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM dictionary_sheets_jobs WHERE id = %s",
                (job_id,),
            )
            row = cursor.fetchone()
        return _row_to_job(row) if row else None

    async def get_job_for_user(self, job_id: str, user_id: str) -> SheetsJobRecord | None:
        from decime_api.db.postgres import postgres_cursor

        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM dictionary_sheets_jobs WHERE id = %s AND user_id = %s",
                (job_id, user_id),
            )
            row = cursor.fetchone()
        return _row_to_job(row) if row else None

    async def has_active_export(self, user_id: str) -> bool:
        from decime_api.db.postgres import postgres_cursor

        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM dictionary_sheets_jobs
                WHERE user_id = %s AND kind = 'export'
                  AND status IN ('queued', 'running')
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone() is not None

    async def update_job(
        self,
        job_id: str,
        *,
        status: SheetsJobStatus | None = None,
        report: dict[str, Any] | None = None,
        error_message: str | None | object = _MISSING,
        accepted_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> SheetsJobRecord | None:
        import json

        from decime_api.db.postgres import postgres_cursor

        job = await self.get_job(job_id)
        if job is None:
            return None
        if job.status in ("completed", "failed"):
            return job
        target = status if status is not None else job.status
        allowed = list(
            allowed_previous_statuses(target) if status is not None else _ACTIVE_STATUSES
        )
        if job.status not in allowed:
            return job
        new_report = report if report is not None else job.report
        new_error = job.error_message if error_message is _MISSING else error_message
        new_accepted = accepted_at if accepted_at is not None else job.accepted_at
        new_finished = finished_at if finished_at is not None else job.finished_at
        now = datetime.now(UTC)
        # The WHERE clause is the atomic gate. Two transactions can both read
        # ``queued``; only the first UPDATE whose previous status still matches
        # commits. The loser returns the row the winner left behind.
        with postgres_cursor() as cursor:
            cursor.execute(
                JOB_STATUS_UPDATE_SQL,
                (
                    target,
                    json.dumps(new_report),
                    new_error,
                    new_accepted,
                    new_finished,
                    now,
                    job_id,
                    allowed,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            return await self.get_job(job_id)
        return _row_to_job(row)

    async def mark_timed_out_jobs(self, *, older_than: datetime) -> int:
        from decime_api.db.postgres import postgres_cursor

        now = datetime.now(UTC)
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                UPDATE dictionary_sheets_jobs
                SET status = 'failed',
                    error_message = 'Job timed out waiting for n8n workflow',
                    finished_at = %s,
                    updated_at = %s
                WHERE status IN ('queued', 'running') AND updated_at < %s
                """,
                (now, now, older_than),
            )
            return cursor.rowcount

    async def get_import_row(
        self, job_id: str, source_row_number: int
    ) -> SheetsImportRowRecord | None:
        from decime_api.db.postgres import postgres_cursor

        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM dictionary_sheets_import_rows
                WHERE job_id = %s AND source_row_number = %s
                """,
                (job_id, source_row_number),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return SheetsImportRowRecord(
            job_id=str(row["job_id"]),
            source_row_number=int(row["source_row_number"]),
            status=row["status"],
            item_id=str(row["item_id"]) if row.get("item_id") else None,
            message=row.get("message"),
            created_at=_as_dt(row["created_at"]),
        )

    async def save_import_row(self, row: SheetsImportRowRecord) -> SheetsImportRowRecord:
        from decime_api.db.postgres import postgres_cursor

        existing = await self.get_import_row(row.job_id, row.source_row_number)
        if existing is not None:
            return existing
        with postgres_cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO dictionary_sheets_import_rows (
                        id, job_id, source_row_number, status, item_id, message, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid4()),
                        row.job_id,
                        row.source_row_number,
                        row.status,
                        row.item_id,
                        row.message,
                        row.created_at,
                    ),
                )
            except Exception:
                # Race: another worker inserted the same (job_id, source_row_number).
                existing = await self.get_import_row(row.job_id, row.source_row_number)
                if existing is not None:
                    return existing
                raise
        return row

    async def count_import_rows(self, job_id: str) -> dict[str, int]:
        from decime_api.db.postgres import postgres_cursor

        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT status, COUNT(*)::int AS cnt
                FROM dictionary_sheets_import_rows
                WHERE job_id = %s
                GROUP BY status
                """,
                (job_id,),
            )
            rows = cursor.fetchall()
        counts = {"created": 0, "skipped_duplicate": 0, "error": 0}
        for row in rows:
            status = row["status"]
            if status in counts:
                counts[status] = int(row["cnt"])
        return counts


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _row_to_job(row: dict[str, Any]) -> SheetsJobRecord:
    import json

    report = row.get("report") or {}
    if isinstance(report, str):
        report = json.loads(report)
    return SheetsJobRecord(
        job_id=str(row["id"]),
        user_id=str(row["user_id"]),
        list_id=str(row["list_id"]),
        kind=row["kind"],
        status=row["status"],
        spreadsheet_id=row.get("spreadsheet_id"),
        sheet_name=row.get("sheet_name"),
        source_spreadsheet_id=row.get("source_spreadsheet_id"),
        source_sheet_name=row.get("source_sheet_name"),
        report=report if isinstance(report, dict) else {},
        error_message=row.get("error_message"),
        accepted_at=_as_dt(row["accepted_at"]) if row.get("accepted_at") else None,
        finished_at=_as_dt(row["finished_at"]) if row.get("finished_at") else None,
        created_at=_as_dt(row["created_at"]),
        updated_at=_as_dt(row["updated_at"]),
    )


_repository: SheetsJobRepository | None = None


def get_sheets_job_repository() -> SheetsJobRepository:
    global _repository
    if _repository is None:
        if settings.use_postgres:
            _repository = PostgresSheetsJobRepository()
        else:
            _repository = MemorySheetsJobRepository()
    return _repository


def reset_sheets_job_repository() -> None:
    global _repository
    _repository = None
