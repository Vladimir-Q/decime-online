"""PostgreSQL-backed training repository with per-user isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from decime_api.db.postgres import postgres_cursor
from decime_api.db.training import (
    ExtractionRecord,
    TrainingItemRecord,
    TrainingListRecord,
)
from decime_api.schemas.training import ReviewGrade, ReviewMode, TrainingCandidate
from decime_api.services.locale import normalize_locale_variant


class PostgresTrainingRepository:
    async def ensure_default_list(self, user_id: str) -> str:
        return self.get_default_list_id(user_id)

    def get_default_list_id(self, user_id: str) -> str:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM training_lists
                WHERE user_id = %s AND name = %s
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (user_id, "My phrases"),
            )
            row = cursor.fetchone()
            if row:
                return str(row["id"])
            list_id = str(uuid4())
            cursor.execute(
                """
                INSERT INTO training_lists (id, user_id, name, source, locale_variant, is_base)
                VALUES (%s, %s, %s, 'manual', 'es-UY-montevideo', true)
                """,
                (list_id, user_id, "My phrases"),
            )
            return list_id

    async def list_lists(self, user_id: str) -> list[TrainingListRecord]:
        self.get_default_list_id(user_id)
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT tl.id, tl.name, tl.locale_variant,
                       COUNT(ti.id) AS item_count
                FROM training_lists tl
                LEFT JOIN training_items ti ON ti.list_id = tl.id AND ti.user_id = tl.user_id
                WHERE tl.user_id = %s
                GROUP BY tl.id, tl.name, tl.locale_variant
                ORDER BY tl.created_at ASC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        return [
            TrainingListRecord(
                list_id=str(row["id"]),
                name=row["name"],
                locale_variant=row["locale_variant"] or "es-UY-montevideo",
                item_count=int(row["item_count"]),
            )
            for row in rows
        ]

    async def list_items(self, user_id: str, list_id: str) -> list[TrainingItemRecord]:
        self._assert_list_owner(user_id, list_id)
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM training_items
                WHERE user_id = %s AND list_id = %s
                ORDER BY created_at DESC
                """,
                (user_id, list_id),
            )
            rows = cursor.fetchall()
        return [_row_to_item(row) for row in rows]

    async def get_item(self, user_id: str, item_id: str) -> TrainingItemRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM training_items WHERE user_id = %s AND id = %s",
                (user_id, item_id),
            )
            row = cursor.fetchone()
        return _row_to_item(row) if row else None

    async def get_due_items(
        self,
        user_id: str,
        list_id: str,
        *,
        limit: int,
        now: datetime,
    ) -> list[TrainingItemRecord]:
        self._assert_list_owner(user_id, list_id)
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM training_items
                WHERE user_id = %s AND list_id = %s AND next_review_at <= %s
                ORDER BY next_review_at ASC, created_at ASC
                LIMIT %s
                """,
                (user_id, list_id, now, limit),
            )
            rows = cursor.fetchall()
        return [_row_to_item(row) for row in rows]

    async def count_due_items(self, user_id: str, list_id: str, *, now: datetime) -> int:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS count FROM training_items
                WHERE user_id = %s AND list_id = %s AND next_review_at <= %s
                """,
                (user_id, list_id, now),
            )
            row = cursor.fetchone()
        return int(row["count"]) if row else 0

    async def update_item_schedule(
        self,
        user_id: str,
        *,
        item_id: str,
        review_stage: int,
        next_review_at: datetime,
    ) -> None:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                UPDATE training_items
                SET review_stage = %s, next_review_at = %s, updated_at = %s
                WHERE user_id = %s AND id = %s
                """,
                (review_stage, next_review_at, datetime.now(UTC), user_id, item_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Training item not found")

    async def record_review_attempt(
        self,
        user_id: str,
        *,
        item_id: str,
        review_mode: ReviewMode,
        grade: ReviewGrade,
        response_latency_ms: int,
        used_hint: bool,
    ) -> None:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO training_attempts
                    (user_id, item_id, review_mode, grade, response_latency_ms, used_hint)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, item_id, review_mode, grade, response_latency_ms, used_hint),
            )

    async def get_known_canonical_keys(
        self, user_id: str, list_id: str | None = None
    ) -> set[str]:
        query = "SELECT canonical_key FROM training_items WHERE user_id = %s AND canonical_key IS NOT NULL"
        params: list = [user_id]
        if list_id:
            query += " AND list_id = %s"
            params.append(list_id)
        with postgres_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return {row["canonical_key"] for row in rows if row["canonical_key"]}

    async def save_extraction(self, user_id: str, record: ExtractionRecord) -> None:
        candidates_json = [c.model_dump(mode="json") for c in record.candidates]
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO extraction_runs
                    (id, user_id, source_type, source_language, source_original_text,
                     spanish_text, target_locale, raw_candidates, provider, model)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (
                    record.extraction_id,
                    user_id,
                    record.source_type,
                    record.source_language,
                    record.source_original_text,
                    record.spanish_text,
                    record.target_locale,
                    json.dumps(candidates_json),
                    record.provider,
                    record.model,
                ),
            )

    async def get_extraction(self, user_id: str, extraction_id: str) -> ExtractionRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM extraction_runs WHERE user_id = %s AND id = %s",
                (user_id, extraction_id),
            )
            row = cursor.fetchone()
        if not row:
            return None
        raw = row.get("raw_candidates") or []
        if isinstance(raw, str):
            raw = json.loads(raw)
        candidates = [TrainingCandidate.model_validate(item) for item in raw]
        created_at = row["created_at"]
        if not isinstance(created_at, datetime):
            created_at = datetime.fromisoformat(str(created_at))
        return ExtractionRecord(
            extraction_id=str(row["id"]),
            source_type=row["source_type"],
            source_language=row.get("source_language") or "ru",
            source_original_text=row.get("source_original_text"),
            spanish_text=row["spanish_text"],
            target_locale=row.get("target_locale") or "es-UY-montevideo",
            candidates=candidates,
            provider=row.get("provider") or "unknown",
            model=row.get("model") or "unknown",
            created_at=created_at,
        )

    async def add_items(self, user_id: str, items: list[TrainingItemRecord]) -> None:
        now = datetime.now(UTC)
        with postgres_cursor() as cursor:
            for item in items:
                candidate = item.candidate
                cursor.execute(
                    """
                    INSERT INTO training_items (
                        id, user_id, list_id, item_type, surface_text, display_text, lemma,
                        locale_variant, translations_ru, translations_en,
                        context_translation_ru, context_translation_en,
                        grammar, governance, example_es, example_ru, example_en,
                        audio_id, source_type, source_language, source_original_text,
                        status, canonical_key, next_review_at, review_stage, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                        %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s,
                        %s, %s, %s, %s, 'approved', %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        item.item_id,
                        user_id,
                        item.list_id,
                        candidate.item_type,
                        candidate.surface_text,
                        candidate.display_text,
                        candidate.lemma,
                        normalize_locale_variant(candidate.locale_variant),
                        json.dumps(candidate.translations_ru),
                        json.dumps(candidate.translations_en),
                        candidate.context_translation_ru,
                        candidate.context_translation_en,
                        json.dumps(candidate.grammar),
                        json.dumps(candidate.governance),
                        candidate.example_es,
                        candidate.example_ru,
                        candidate.example_en,
                        item.audio_id,
                        None,
                        None,
                        None,
                        item.canonical_key,
                        item.next_review_at,
                        item.review_stage,
                        now,
                        now,
                    ),
                )

    async def delete_item(self, user_id: str, item_id: str) -> bool:
        with postgres_cursor() as cursor:
            cursor.execute(
                "DELETE FROM training_attempts WHERE user_id = %s AND item_id = %s",
                (user_id, item_id),
            )
            cursor.execute(
                "DELETE FROM training_items WHERE user_id = %s AND id = %s",
                (user_id, item_id),
            )
            return cursor.rowcount > 0

    async def update_item_audio(
        self,
        user_id: str,
        *,
        item_id: str,
        audio_id: str,
        audio_status: str = "ready",
    ) -> TrainingItemRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                UPDATE training_items
                SET audio_id = %s, updated_at = %s
                WHERE user_id = %s AND id = %s
                """,
                (audio_id, datetime.now(UTC), user_id, item_id),
            )
            if cursor.rowcount == 0:
                return None
        return await self.get_item(user_id, item_id)

    async def clear(self, user_id: str) -> None:
        with postgres_cursor() as cursor:
            cursor.execute("DELETE FROM training_attempts WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM training_items WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM extraction_runs WHERE user_id = %s", (user_id,))

    def _assert_list_owner(self, user_id: str, list_id: str) -> None:
        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM training_lists WHERE user_id = %s AND id = %s",
                (user_id, list_id),
            )
            if not cursor.fetchone():
                raise ValueError("Training list not found")


def _row_to_item(row: dict) -> TrainingItemRecord:
    grammar = row.get("grammar") or {}
    if isinstance(grammar, str):
        grammar = json.loads(grammar)
    governance = row.get("governance") or []
    if isinstance(governance, str):
        governance = json.loads(governance)
    translations_ru = row.get("translations_ru") or []
    if isinstance(translations_ru, str):
        translations_ru = json.loads(translations_ru)
    translations_en = row.get("translations_en") or []
    if isinstance(translations_en, str):
        translations_en = json.loads(translations_en)

    candidate = TrainingCandidate(
        candidate_id=str(row["id"]),
        item_type=row["item_type"],
        surface_text=row["surface_text"],
        display_text=row["display_text"],
        lemma=row.get("lemma"),
        locale_variant=row.get("locale_variant") or "es-UY-montevideo",
        translations_ru=translations_ru,
        translations_en=translations_en,
        context_translation_ru=row.get("context_translation_ru"),
        context_translation_en=row.get("context_translation_en"),
        grammar=grammar,
        governance=governance,
        example_es=row.get("example_es"),
        example_ru=row.get("example_ru"),
        example_en=row.get("example_en"),
        canonical_key=row.get("canonical_key"),
    )
    created_at = row["created_at"]
    next_review_at = row["next_review_at"]
    if not isinstance(created_at, datetime):
        created_at = datetime.fromisoformat(str(created_at))
    if not isinstance(next_review_at, datetime):
        next_review_at = datetime.fromisoformat(str(next_review_at))
    audio_id = str(row["audio_id"]) if row.get("audio_id") else None
    return TrainingItemRecord(
        item_id=str(row["id"]),
        list_id=str(row["list_id"]),
        candidate=candidate,
        canonical_key=row.get("canonical_key") or "",
        audio_id=audio_id,
        audio_status="ready" if audio_id else "none",
        review_stage=int(row.get("review_stage") or 0),
        next_review_at=next_review_at,
        created_at=created_at,
    )
