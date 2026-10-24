"""PostgreSQL connection pool and SQL migration runner."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from decime_api.config import settings

logger = logging.getLogger(__name__)

# config.py lives one level above db/; repo root is /app in Docker and repo root locally.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_MIGRATIONS_DIR = _REPO_ROOT / "supabase" / "migrations"

_pool: psycopg.Connection | None = None


def use_postgres() -> bool:
    return bool(settings.database_url)


def get_connection() -> psycopg.Connection:
    global _pool
    if _pool is None or _pool.closed:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        _pool = psycopg.connect(settings.database_url, row_factory=dict_row)
        _pool.autocommit = False
    return _pool


@contextmanager
def postgres_cursor() -> Generator[psycopg.Cursor, None, None]:
    connection = get_connection()
    with connection.cursor() as cursor:
        try:
            yield cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def close_postgres() -> None:
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.close()
    _pool = None


def run_migrations() -> None:
    if not settings.database_url:
        return

    migrations_dir = _MIGRATIONS_DIR
    if not migrations_dir.is_dir():
        logger.warning("Migrations directory not found: %s", migrations_dir)
        return

    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.commit()

        cursor.execute("SELECT filename FROM schema_migrations")
        applied = {row["filename"] for row in cursor.fetchall()}

        for path in sorted(migrations_dir.glob("*.sql")):
            if path.name in applied:
                continue
            logger.info("Applying migration %s", path.name)
            sql = path.read_text(encoding="utf-8")
            cursor.execute(sql)
            cursor.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (path.name,),
            )
            connection.commit()
            logger.info("Applied migration %s", path.name)
