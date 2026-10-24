"""PostgreSQL-backed user store (replaces SQLite when DATABASE_URL is set)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from decime_api.db.postgres import postgres_cursor
from decime_api.db.user_store import UserRecord
from decime_api.services.auth.passwords import hash_password


class PostgresUserStore:
    def init_db(self) -> None:
        # Migrations create app_users; nothing extra required here.
        return

    def count_users(self) -> int:
        with postgres_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM app_users")
            row = cursor.fetchone()
            return int(row["count"]) if row else 0

    def create_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None,
        role: str,
        is_active: bool = True,
    ) -> UserRecord:
        user_id = str(uuid4())
        now = datetime.now(UTC)
        normalized_email = email.strip().lower()
        password_hash = hash_password(password)

        with postgres_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_users (id, email, password_hash, display_name, role, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    normalized_email,
                    password_hash,
                    display_name,
                    role,
                    is_active,
                    now,
                    now,
                ),
            )
            _ensure_default_training_list(cursor, user_id)

        record = self.get_by_id(user_id)
        assert record is not None
        return record

    def get_by_email(self, email: str) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM app_users WHERE lower(email) = lower(%s)",
                (email.strip(),),
            )
            row = cursor.fetchone()
        return _row_to_record(row) if row else None

    def get_by_id(self, user_id: str) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute("SELECT * FROM app_users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
        return _row_to_record(row) if row else None

    def list_users(self) -> list[UserRecord]:
        with postgres_cursor() as cursor:
            cursor.execute("SELECT * FROM app_users ORDER BY created_at ASC")
            rows = cursor.fetchall()
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
        now = datetime.now(UTC)

        with postgres_cursor() as cursor:
            cursor.execute(
                """
                UPDATE app_users
                SET display_name = %s, role = %s, is_active = %s, password_hash = %s,
                    app_language = %s, updated_at = %s
                WHERE id = %s
                """,
                (
                    next_display,
                    next_role,
                    next_active,
                    next_hash,
                    next_language,
                    now,
                    user_id,
                ),
            )
        return self.get_by_id(user_id)


def _ensure_default_training_list(cursor, user_id: str) -> None:
    cursor.execute(
        "SELECT id FROM training_lists WHERE user_id = %s AND name = %s LIMIT 1",
        (user_id, "My phrases"),
    )
    if cursor.fetchone():
        return
    cursor.execute(
        """
        INSERT INTO training_lists (user_id, name, source, locale_variant, is_base)
        VALUES (%s, %s, 'manual', 'es-UY-montevideo', true)
        """,
        (user_id, "My phrases"),
    )


def _row_to_record(row: dict) -> UserRecord:
    created_at = row["created_at"]
    updated_at = row["updated_at"]
    if not isinstance(created_at, datetime):
        created_at = datetime.fromisoformat(str(created_at))
    if not isinstance(updated_at, datetime):
        updated_at = datetime.fromisoformat(str(updated_at))
    return UserRecord(
        id=str(row["id"]),
        email=row["email"],
        password_hash=row["password_hash"],
        display_name=row.get("display_name"),
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=created_at,
        updated_at=updated_at,
        app_language=row.get("app_language"),
    )
