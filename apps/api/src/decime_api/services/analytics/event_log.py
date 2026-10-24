"""Append-only product analytics events (n8n reads from Postgres)."""

from __future__ import annotations

import json
import logging
from typing import Any

from decime_api.db.postgres import postgres_cursor, use_postgres

logger = logging.getLogger(__name__)

EVENT_REPLY_GENERATED = "reply_generated"
EVENT_CANDIDATE_APPROVED = "candidate_approved"
EVENT_REVIEW_COMPLETED = "review_completed"
EVENT_AUDIO_TRANSCRIBED = "audio_transcribed"
EVENT_AUDIO_GENERATED = "audio_generated"
EVENT_ERROR_OCCURRED = "error_occurred"


async def log_event(
    user_id: str | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if not use_postgres():
        logger.debug("event_log skip (no postgres): %s %s", event_type, payload)
        return
    try:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO event_log (user_id, event_type, payload)
                VALUES (%s, %s, %s::jsonb)
                """,
                (user_id, event_type, json.dumps(payload or {})),
            )
    except Exception:
        logger.exception("Failed to write event_log %s", event_type)
