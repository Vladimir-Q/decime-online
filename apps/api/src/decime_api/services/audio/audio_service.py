from __future__ import annotations

import logging
from threading import Lock
from uuid import uuid4

from decime_api.config import settings
from decime_api.db.postgres_audio import register_audio_file, register_stored_audio
from decime_api.schemas.audio import (
    SynthesizeAudioRequest,
    SynthesizeAudioResponse,
    SynthesizeJobStatusResponse,
    TranscribeAudioResponse,
)
from decime_api.services.ai.speech_provider import STTProvider, TTSProvider
from decime_api.services.analytics.event_log import (
    EVENT_AUDIO_GENERATED,
    EVENT_AUDIO_TRANSCRIBED,
    log_event,
)
from decime_api.services.storage.audio_cache import tts_cache_key
from decime_api.services.storage.audio_storage import LocalAudioStorage, sanitize_audio_extension

logger = logging.getLogger(__name__)

_transcripts: dict[str, dict] = {}
_jobs: dict[str, dict] = {}
_jobs_lock = Lock()


async def transcribe_upload(
    *,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    language_hint: str,
    source_type: str,
    stt: STTProvider,
    storage: LocalAudioStorage,
) -> TranscribeAudioResponse:
    stored = storage.save_bytes(
        file_bytes,
        mime_type=mime_type or "application/octet-stream",
        extension=_extension_from_filename(filename),
        provider=stt.provider_name,
        model=stt.model_name,
        user_id=user_id,
    )
    register_stored_audio(stored, source_type=source_type or "user_voice")
    result = await stt.transcribe(file_bytes, filename=filename, language_hint=language_hint)
    transcript_id = str(uuid4())
    _transcripts[transcript_id] = {
        "transcript_id": transcript_id,
        "audio_id": stored.audio_id,
        "language": result.language,
        "transcript": result.transcript,
        "source_type": source_type,
        "user_id": user_id,
    }
    await log_event(
        user_id,
        EVENT_AUDIO_TRANSCRIBED,
        {"audio_id": stored.audio_id, "language": result.language},
    )
    return TranscribeAudioResponse(
        audio_id=stored.audio_id,
        transcript_id=transcript_id,
        language=result.language,
        transcript=result.transcript,
        confidence_notes=result.confidence_notes,
    )


def _tts_voice_for_provider(tts: TTSProvider) -> str:
    if tts.provider_name == "orpheus":
        return settings.orpheus_tts_voice
    if tts.provider_name == "openai":
        return settings.openai_tts_voice
    return "fake"


async def synthesize_text(
    user_id: str,
    request: SynthesizeAudioRequest,
    tts: TTSProvider,
    storage: LocalAudioStorage,
) -> SynthesizeAudioResponse:
    """Synchronous synthesize (training / internal). Always waits for audio."""
    voice = _tts_voice_for_provider(tts)
    cache_key = tts_cache_key(
        text=request.text,
        locale=request.locale,
        model=tts.model_name,
        voice=voice,
        mode=request.mode,
        speed=request.speed,
    )
    cached = storage.find_by_text_hash(cache_key, user_id=user_id)
    if cached:
        register_audio_file(storage, cached.audio_id, user_id=user_id, source_type="tts")
        return SynthesizeAudioResponse(
            audio_id=cached.audio_id,
            audio_url=_public_audio_url(cached.audio_id),
            cached=True,
            status="ready",
        )

    result = await tts.synthesize(
        request.text,
        locale=request.locale,
        mode=request.mode,
        speed=request.speed,
        voice=voice,
    )
    stored = storage.save_bytes(
        result.audio_bytes,
        mime_type=result.mime_type,
        extension=result.extension,
        text_hash=cache_key,
        provider=tts.provider_name,
        model=tts.model_name,
        voice=voice,
        user_id=user_id,
    )
    register_stored_audio(stored, source_type="tts")
    await log_event(
        user_id,
        EVENT_AUDIO_GENERATED,
        {"audio_id": stored.audio_id, "cached": False},
    )
    return SynthesizeAudioResponse(
        audio_id=stored.audio_id,
        audio_url=_public_audio_url(stored.audio_id),
        cached=False,
        status="ready",
    )


async def begin_synthesize_job(
    user_id: str,
    request: SynthesizeAudioRequest,
    tts: TTSProvider,
    storage: LocalAudioStorage,
) -> SynthesizeAudioResponse:
    """Start TTS without blocking the HTTP response (Cloudflare ~100s limit).

    Fake provider stays synchronous. Cache hits return ready immediately.
    """
    voice = _tts_voice_for_provider(tts)
    cache_key = tts_cache_key(
        text=request.text,
        locale=request.locale,
        model=tts.model_name,
        voice=voice,
        mode=request.mode,
        speed=request.speed,
    )
    cached = storage.find_by_text_hash(cache_key, user_id=user_id)
    if cached:
        register_audio_file(storage, cached.audio_id, user_id=user_id, source_type="tts")
        return SynthesizeAudioResponse(
            audio_id=cached.audio_id,
            audio_url=_public_audio_url(cached.audio_id),
            cached=True,
            status="ready",
        )

    if tts.provider_name == "fake":
        return await synthesize_text(user_id, request, tts, storage)

    job_id = str(uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "user_id": user_id,
            "status": "pending",
            "audio_id": "",
            "audio_url": "",
            "cached": False,
            "error": None,
            "request": request.model_copy(),
            "cache_key": cache_key,
            "voice": voice,
        }
    return SynthesizeAudioResponse(
        status="pending",
        job_id=job_id,
        audio_id="",
        audio_url="",
        cached=False,
    )


async def run_synthesize_job(
    job_id: str,
    tts: TTSProvider,
    storage: LocalAudioStorage,
) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        request: SynthesizeAudioRequest = job["request"]
        user_id: str = job["user_id"]
        cache_key: str = job["cache_key"]
        voice: str = job["voice"]

    try:
        cached = storage.find_by_text_hash(cache_key, user_id=user_id)
        if cached:
            register_audio_file(storage, cached.audio_id, user_id=user_id, source_type="tts")
            with _jobs_lock:
                _jobs[job_id].update(
                    {
                        "status": "ready",
                        "audio_id": cached.audio_id,
                        "audio_url": _public_audio_url(cached.audio_id),
                        "cached": True,
                        "error": None,
                    }
                )
            return

        result = await tts.synthesize(
            request.text,
            locale=request.locale,
            mode=request.mode,
            speed=request.speed,
            voice=voice,
        )
        stored = storage.save_bytes(
            result.audio_bytes,
            mime_type=result.mime_type,
            extension=result.extension,
            text_hash=cache_key,
            provider=tts.provider_name,
            model=tts.model_name,
            voice=voice,
            user_id=user_id,
        )
        register_stored_audio(stored, source_type="tts")
        await log_event(
            user_id,
            EVENT_AUDIO_GENERATED,
            {"audio_id": stored.audio_id, "cached": False, "job_id": job_id},
        )
        with _jobs_lock:
            _jobs[job_id].update(
                {
                    "status": "ready",
                    "audio_id": stored.audio_id,
                    "audio_url": _public_audio_url(stored.audio_id),
                    "cached": False,
                    "error": None,
                }
            )
        logger.info("tts job ready job_id=%s audio_id=%s", job_id, stored.audio_id)
    except Exception as error:
        logger.exception("tts job failed job_id=%s", job_id)
        message = str(error)
        # Never leak internal hostnames/paths to the client job payload.
        if "orpheus" in message.lower() or "http://" in message or "https://" in message:
            message = "Voice synthesis is temporarily unavailable. Please try again shortly."
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id].update({"status": "error", "error": message})


def get_synthesize_job(job_id: str, user_id: str) -> SynthesizeJobStatusResponse | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job or job.get("user_id") != user_id:
            return None
        return SynthesizeJobStatusResponse(
            job_id=job_id,
            status=job["status"],
            audio_id=job.get("audio_id") or "",
            audio_url=job.get("audio_url") or "",
            cached=bool(job.get("cached")),
            error=job.get("error"),
        )


def reset_synthesize_jobs() -> None:
    """Tests only."""
    with _jobs_lock:
        _jobs.clear()


def clear_user_audio_data(storage: LocalAudioStorage, user_id: str) -> None:
    storage.clear_user(user_id)
    to_delete = [tid for tid, row in _transcripts.items() if row.get("user_id") == user_id]
    for tid in to_delete:
        _transcripts.pop(tid, None)


def clear_audio_data(storage: LocalAudioStorage) -> None:
    storage.clear_all()
    _transcripts.clear()


def _public_audio_url(audio_id: str) -> str:
    return f"{settings.api_base_url}/api/v1/audio/files/{audio_id}"


def _extension_from_filename(filename: str) -> str:
    if "." in filename:
        return sanitize_audio_extension(filename.rsplit(".", 1)[-1])
    return sanitize_audio_extension(None)
