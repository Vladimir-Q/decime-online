import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from decime_api.config import settings
from decime_api.services.auth.passwords import hash_password

if TYPE_CHECKING:
    from decime_api.db.postgres_user_store import PostgresUserStore


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    display_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    app_language: str | None = None


class UserStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    app_language TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "app_language" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN app_language TEXT")

    def count_users(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM users").fetchone()
            return int(row[0]) if row else 0

    def create_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None,
        role: str,
        is_active: bool = True,
    ) -> UserRecord:
        now = _now_iso()
        record = UserRecord(
            id=str(uuid4()),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            display_name=display_name,
            role=role,
            is_active=is_active,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            app_language=None,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    id, email, password_hash, display_name, role, is_active,
                    created_at, updated_at, app_language
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.email,
                    record.password_hash,
                    record.display_name,
                    record.role,
                    1 if record.is_active else 0,
                    now,
                    now,
                    record.app_language,
                ),
            )
        return record

    def get_by_email(self, email: str) -> UserRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
                (email.strip().lower(),),
            ).fetchone()
        return _row_to_record(row) if row else None

    def get_by_id(self, user_id: str) -> UserRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_users(self) -> list[UserRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM users ORDER BY created_at ASC"
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def update_user(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        password: str | None = None,
        app_language: str | None = None,
        clear_app_language: bool = False,
    ) -> UserRecord | None:
        existing = self.get_by_id(user_id)
        if not existing:
            return None

        next_display = existing.display_name if display_name is None else display_name
        next_role = existing.role if role is None else role
        next_active = existing.is_active if is_active is None else is_active
        next_hash = (
            existing.password_hash if password is None else hash_password(password)
        )
        if clear_app_language:
            next_language = None
        elif app_language is None:
            next_language = existing.app_language
        else:
            next_language = app_language
        now = _now_iso()

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET display_name = ?, role = ?, is_active = ?, password_hash = ?,
                    app_language = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_display,
                    next_role,
                    1 if next_active else 0,
                    next_hash,
                    next_language,
                    now,
                    user_id,
                ),
            )
        return self.get_by_id(user_id)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection


_user_store: "UserStore | PostgresUserStore | None" = None


def get_user_store() -> "UserStore | PostgresUserStore":
    global _user_store
    if _user_store is None:
        from decime_api.db.postgres_user_store import PostgresUserStore

        if settings.use_postgres:
            _user_store = PostgresUserStore()
        else:
            _user_store = UserStore(settings.auth_database_file)
            _user_store.init_db()
    return _user_store


def reset_user_store() -> None:
    global _user_store
    _user_store = None


def bootstrap_admin_if_configured() -> None:
    email = settings.auth_bootstrap_admin_email
    password = settings.auth_bootstrap_admin_password
    if not email or not password:
        return

    store = get_user_store()
    if store.count_users() > 0:
        return

    store.create_user(
        email=email,
        password=password,
        display_name="Admin",
        role="admin",
        is_active=True,
    )


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _row_to_record(row: sqlite3.Row) -> UserRecord:
    keys = row.keys()
    app_language = row["app_language"] if "app_language" in keys else None
    return UserRecord(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        display_name=row["display_name"],
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        app_language=app_language,
    )
