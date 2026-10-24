"""Register local audio files in Postgres so FK targets (training_items.audio_id) resolve."""

from __future__ import annotations

import logging

from decime_api.db.postgres import postgres_cursor, use_postgres
from decime_api.services.storage.audio_storage import LocalAudioStorage, StoredAudio

logger = logging.getLogger(__name__)


def register_audio_file(
    storage: LocalAudioStorage,
    audio_id: str,
    *,
    user_id: str,
    source_type: str = "tts",
) -> None:
    """Upsert audio_files row for a file already present in LocalAudioStorage.

    No-op when DATABASE_URL is unset (JSON/memory repos have no FK).
    """
    if not use_postgres():
        return
    stored = storage.get(audio_id, user_id=user_id)
    if stored is None:
        logger.warning("register_audio_file: missing local audio_id=%s user=%s", audio_id, user_id)
        return
    _upsert_stored(stored, source_type=source_type)


def register_stored_audio(stored: StoredAudio, *, source_type: str = "tts") -> None:
    if not use_postgres():
        return
    if not stored.user_id:
        logger.warning("register_stored_audio: skipping audio_id=%s without user_id", stored.audio_id)
        return
    _upsert_stored(stored, source_type=source_type)


def _upsert_stored(stored: StoredAudio, *, source_type: str) -> None:
    try:
        relative = str(stored.storage_path)
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audio_files (
                    id, user_id, source_type, storage_path, mime_type,
                    provider, model, voice, text_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    storage_path = EXCLUDED.storage_path,
                    mime_type = COALESCE(EXCLUDED.mime_type, audio_files.mime_type),
                    provider = COALESCE(EXCLUDED.provider, audio_files.provider),
                    model = COALESCE(EXCLUDED.model, audio_files.model),
                    voice = COALESCE(EXCLUDED.voice, audio_files.voice),
                    text_hash = COALESCE(EXCLUDED.text_hash, audio_files.text_hash)
                """,
                (
                    stored.audio_id,
                    stored.user_id,
                    source_type,
                    relative,
                    stored.mime_type,
                    stored.provider,
                    stored.model,
                    stored.voice,
                    stored.text_hash,
                ),
            )
    except Exception:
        logger.exception("Failed to register audio_files id=%s", stored.audio_id)
        raise
