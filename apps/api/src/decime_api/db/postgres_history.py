"""PostgreSQL-backed compose history with per-user isolation."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from decime_api.db.postgres import postgres_cursor
from decime_api.schemas.compose import ReplyBundle, TranslateToEsRequest
from decime_api.schemas.history import HistoryItem, HistoryListResponse


class PostgresHistoryRepository:
    async def save_request(self, user_id: str, request: TranslateToEsRequest) -> str:
        request_id = str(uuid4())
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO reply_requests (
                    id, user_id, source_language, source_text, incoming_text,
                    channel, tone, situation_code, target_locale, user_level, source_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request_id,
                    user_id,
                    request.source_language,
                    request.source_text,
                    None,
                    request.context.channel,
                    None,
                    None,
                    request.context.target_locale,
                    request.context.user_level,
                    "translate_text",
                ),
            )
        return request_id

    async def save_output(
        self,
        user_id: str,
        request_id: str,
        bundle: ReplyBundle,
        *,
        provider: str,
        model: str,
        latency_ms: int,
    ) -> None:
        with postgres_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM reply_requests WHERE id = %s AND user_id = %s",
                (request_id, user_id),
            )
            if not cursor.fetchone():
                raise ValueError("Reply request not found")
            cursor.execute(
                """
                INSERT INTO reply_outputs (
                    request_id, recommended_reply, simple_reply, short_reply, more_formal_reply,
                    intent_summary_ru, intent_summary_en, notes_ru, notes_en, warnings,
                    dialect_stamp, raw_json, provider, model, latency_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s)
                """,
                (
                    request_id,
                    bundle.recommended_reply,
                    None,
                    None,
                    None,
                    bundle.intent_summary_ru,
                    bundle.intent_summary_en,
                    json.dumps([]),
                    json.dumps([]),
                    json.dumps(bundle.warnings),
                    bundle.dialect_stamp,
                    json.dumps(bundle.model_dump(mode="json")),
                    provider,
                    model,
                    latency_ms,
                ),
            )

    async def list_history(self, user_id: str, *, limit: int = 20) -> HistoryListResponse:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT rr.id AS request_id, rr.created_at, rr.source_language, rr.source_text,
                       rr.incoming_text, rr.channel, rr.tone, rr.situation_code,
                       ro.recommended_reply, ro.dialect_stamp, ro.provider, ro.model
                FROM reply_requests rr
                JOIN reply_outputs ro ON ro.request_id = rr.id
                WHERE rr.user_id = %s
                ORDER BY rr.created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()

        items: list[HistoryItem] = []
        for row in rows:
            created_at = row["created_at"]
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()
            items.append(
                HistoryItem(
                    request_id=str(row["request_id"]),
                    created_at=str(created_at),
                    source_language=row.get("source_language"),
                    source_text=row.get("source_text"),
                    incoming_text=row.get("incoming_text"),
                    channel=row.get("channel"),
                    tone=row.get("tone"),
                    situation=row.get("situation_code"),
                    recommended_reply=row["recommended_reply"],
                    dialect_stamp=row.get("dialect_stamp"),
                    provider=row.get("provider"),
                    model=row.get("model"),
                )
            )
        return HistoryListResponse(items=items, total=len(items))

    async def clear(self, user_id: str) -> None:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM reply_outputs
                WHERE request_id IN (SELECT id FROM reply_requests WHERE user_id = %s)
                """,
                (user_id,),
            )
            cursor.execute("DELETE FROM reply_requests WHERE user_id = %s", (user_id,))
