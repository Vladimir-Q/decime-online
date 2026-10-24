"""Atomic sheets-job transitions. PostgreSQL cases need DECIME_SHEETS_PG_URL."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from threading import Barrier, Thread
from uuid import uuid4

import pytest

from decime_api.db.sheets_jobs import (
    JOB_STATUS_UPDATE_SQL,
    MemorySheetsJobRepository,
    PostgresSheetsJobRepository,
    SheetsJobRecord,
    allowed_previous_statuses,
)

_PG_URL = os.environ.get("DECIME_SHEETS_PG_URL", "")


def _job(**overrides: object) -> SheetsJobRecord:
    now = datetime.now(UTC)
    base = SheetsJobRecord(
        job_id=str(uuid4()),
        user_id=str(uuid4()),
        list_id=str(uuid4()),
        kind="export",
        status="queued",
        created_at=now,
        updated_at=now,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_allowed_transitions_are_active_only() -> None:
    assert allowed_previous_statuses("running") == ("queued", "running")
    assert allowed_previous_statuses("completed") == ("queued", "running")
    assert allowed_previous_statuses("failed") == ("queued", "running")
    assert allowed_previous_statuses("queued") == ()


@pytest.mark.asyncio
async def test_memory_terminal_status_is_sticky() -> None:
    repo = MemorySheetsJobRepository()
    job = _job()
    await repo.create_job(job)
    done = await repo.update_job(
        job.job_id,
        status="completed",
        report={"exported_rows": 2},
        finished_at=datetime(2026, 10, 19, tzinfo=UTC),
    )
    assert done is not None
    assert done.status == "completed"

    running = await repo.update_job(job.job_id, status="running")
    assert running is not None
    assert running.status == "completed"
    assert running.finished_at == done.finished_at

    failed = await repo.update_job(
        job.job_id,
        status="failed",
        error_message="late",
        report={"exported_rows": 9},
    )
    assert failed is not None
    assert failed.status == "completed"
    assert failed.error_message is None
    assert failed.report == {"exported_rows": 2}


@pytest.mark.asyncio
async def test_memory_repeat_failure_keeps_first_result() -> None:
    repo = MemorySheetsJobRepository()
    job = _job()
    await repo.create_job(job)
    first_finished = datetime(2026, 10, 19, 1, tzinfo=UTC)
    await repo.update_job(
        job.job_id,
        status="failed",
        error_message="sheet locked",
        finished_at=first_finished,
    )
    again = await repo.update_job(
        job.job_id,
        status="failed",
        error_message="different",
        finished_at=datetime(2026, 10, 19, 2, tzinfo=UTC),
    )
    assert again is not None
    assert again.error_message == "sheet locked"
    assert again.finished_at == first_finished


@pytest.mark.asyncio
async def test_memory_second_active_export_uses_same_user() -> None:
    repo = MemorySheetsJobRepository()
    user_id = str(uuid4())
    await repo.create_job(_job(user_id=user_id))
    with pytest.raises(ValueError, match="already in progress"):
        await repo.create_job(_job(user_id=user_id))


def _pg_connect(url: str):
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(url, row_factory=dict_row, autocommit=True)


def _database_name(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path.lstrip("/").split("?")[0]


def _assert_scratch_database(url: str) -> None:
    """Refuse to drop a table unless the URL clearly points at a scratch database."""
    name = _database_name(url)
    if not name or "test" not in name.lower():
        raise RuntimeError(
            "DECIME_SHEETS_PG_URL must use a database whose name contains 'test'. "
            f"Refusing to drop dictionary_sheets_jobs (database={name!r})."
        )
    with _pg_connect(url) as conn:
        row = conn.execute("SELECT current_database() AS name").fetchone()
        current = str(row["name"])
        if current == "decime" or "test" not in current.lower():
            raise RuntimeError(
                "Connected database is not a scratch test database "
                f"({current!r}). Refusing to drop dictionary_sheets_jobs."
            )
        foreign_key = conn.execute(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = 'dictionary_sheets_jobs'
              AND constraint_type = 'FOREIGN KEY'
            LIMIT 1
            """
        ).fetchone()
        if foreign_key:
            raise RuntimeError(
                "Refusing to drop dictionary_sheets_jobs because it has foreign keys."
            )


def _ensure_scratch_table(url: str) -> None:
    _assert_scratch_database(url)
    with _pg_connect(url) as conn:
        conn.execute("DROP TABLE IF EXISTS dictionary_sheets_jobs")
        conn.execute(
            """
            CREATE TABLE dictionary_sheets_jobs (
                id uuid primary key,
                user_id uuid not null,
                list_id uuid not null,
                kind text not null,
                status text not null,
                spreadsheet_id text,
                sheet_name text,
                source_spreadsheet_id text,
                source_sheet_name text,
                report jsonb not null default '{}'::jsonb,
                error_message text,
                accepted_at timestamptz,
                finished_at timestamptz,
                created_at timestamptz not null default now(),
                updated_at timestamptz not null default now()
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX dictionary_sheets_jobs_one_active_export_idx
            ON dictionary_sheets_jobs (user_id)
            WHERE kind = 'export' AND status IN ('queued', 'running')
            """
        )


def _insert_queued(url: str) -> str:
    job_id = str(uuid4())
    with _pg_connect(url) as conn:
        conn.execute(
            """
            INSERT INTO dictionary_sheets_jobs (
                id, user_id, list_id, kind, status, report, created_at, updated_at
            ) VALUES (%s, %s, %s, 'export', 'queued', '{}'::jsonb, now(), now())
            """,
            (job_id, str(uuid4()), str(uuid4())),
        )
    return job_id


def _apply(conn, job_id: str, status: str, *, report: str, error: str | None, finished) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute(
            JOB_STATUS_UPDATE_SQL,
            (
                status,
                report,
                error,
                None,
                finished,
                datetime.now(UTC),
                job_id,
                ["queued", "running"],
            ),
        )
        return cursor.fetchone()


@pytest.mark.skipif(not _PG_URL, reason="DECIME_SHEETS_PG_URL is not set")
def test_postgres_completed_callback_beats_later_running() -> None:
    _ensure_scratch_table(_PG_URL)
    job_id = _insert_queued(_PG_URL)
    finished = datetime(2026, 10, 19, 3, tzinfo=UTC)
    with _pg_connect(_PG_URL) as first, _pg_connect(_PG_URL) as second:
        first.autocommit = False
        second.autocommit = False
        written = _apply(
            first, job_id, "completed", report='{"exported_rows": 4}', error=None, finished=finished
        )
        first.commit()
        missed = _apply(second, job_id, "running", report="{}", error=None, finished=None)
        second.commit()
    assert written is not None
    assert missed is None
    with _pg_connect(_PG_URL) as conn:
        row = conn.execute(
            "SELECT status, finished_at, report FROM dictionary_sheets_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    assert row["status"] == "completed"
    assert row["report"]["exported_rows"] == 4


@pytest.mark.skipif(not _PG_URL, reason="DECIME_SHEETS_PG_URL is not set")
def test_postgres_running_then_completed_is_allowed() -> None:
    _ensure_scratch_table(_PG_URL)
    job_id = _insert_queued(_PG_URL)
    with _pg_connect(_PG_URL) as conn:
        conn.autocommit = False
        assert _apply(conn, job_id, "running", report="{}", error=None, finished=None)
        conn.commit()
        written = _apply(
            conn,
            job_id,
            "completed",
            report='{"exported_rows": 0}',
            error=None,
            finished=datetime.now(UTC),
        )
        conn.commit()
    assert written is not None and written["status"] == "completed"


@pytest.mark.skipif(not _PG_URL, reason="DECIME_SHEETS_PG_URL is not set")
def test_postgres_concurrent_callback_and_running_end_completed() -> None:
    """Two sessions race. completed sticks whether it commits before or after running."""
    _ensure_scratch_table(_PG_URL)
    job_id = _insert_queued(_PG_URL)
    barrier = Barrier(2)
    errors: list[BaseException] = []

    def _race(status: str, report: str, finished) -> None:
        try:
            with _pg_connect(_PG_URL) as conn:
                conn.autocommit = False
                barrier.wait(timeout=5)
                _apply(conn, job_id, status, report=report, error=None, finished=finished)
                conn.commit()
        except Exception as exc:  # noqa: BLE001 — the assertion reports the worker failure
            errors.append(exc)

    finished = datetime.now(UTC)
    workers = [
        Thread(
            target=_race,
            args=("completed", '{"exported_rows": 7}', finished),
        ),
        Thread(target=_race, args=("running", "{}", None)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)
    assert errors == []
    with _pg_connect(_PG_URL) as conn:
        row = conn.execute(
            "SELECT status, report FROM dictionary_sheets_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    assert row["status"] == "completed"
    assert row["report"]["exported_rows"] == 7


@pytest.mark.skipif(not _PG_URL, reason="DECIME_SHEETS_PG_URL is not set")
def test_postgres_first_terminal_failure_is_not_replaced() -> None:
    _ensure_scratch_table(_PG_URL)
    job_id = _insert_queued(_PG_URL)
    with _pg_connect(_PG_URL) as conn:
        conn.autocommit = False
        failed = _apply(
            conn,
            job_id,
            "failed",
            report="{}",
            error="n8n webhook timed out",
            finished=datetime(2026, 10, 19, 4, tzinfo=UTC),
        )
        conn.commit()
        late = _apply(
            conn,
            job_id,
            "completed",
            report='{"exported_rows": 1}',
            error=None,
            finished=datetime(2026, 10, 19, 5, tzinfo=UTC),
        )
        conn.commit()
    assert failed is not None
    assert late is None
    with _pg_connect(_PG_URL) as conn:
        row = conn.execute(
            "SELECT status, error_message, report FROM dictionary_sheets_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    assert row["status"] == "failed"
    assert row["error_message"] == "n8n webhook timed out"
    assert row["report"] == {}


@pytest.mark.skipif(not _PG_URL, reason="DECIME_SHEETS_PG_URL is not set")
@pytest.mark.asyncio
async def test_postgres_repository_refuses_running_after_completed(monkeypatch) -> None:
    from decime_api.config import settings
    from decime_api.db.postgres import close_postgres

    _ensure_scratch_table(_PG_URL)
    monkeypatch.setattr(settings, "database_url", _PG_URL)
    close_postgres()
    repo = PostgresSheetsJobRepository()
    job = _job()
    try:
        await repo.create_job(job)
        done = await repo.update_job(
            job.job_id,
            status="completed",
            report={"exported_rows": 1},
            finished_at=datetime(2026, 10, 19, 6, tzinfo=UTC),
        )
        assert done is not None and done.status == "completed"
        later = await repo.update_job(job.job_id, status="running", accepted_at=datetime.now(UTC))
        assert later is not None
        assert later.status == "completed"
        assert later.finished_at == done.finished_at
        assert later.report == {"exported_rows": 1}
    finally:
        close_postgres()
