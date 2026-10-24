from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from decime_api.auth.dependencies import CurrentUser, get_current_user
from decime_api.auth.user_scope import resolve_user_id
from decime_api.dependencies import get_audio_storage, get_stt_provider, get_tts_provider
from decime_api.schemas.audio import (
    SynthesizeAudioRequest,
    SynthesizeAudioResponse,
    SynthesizeJobStatusResponse,
    TranscribeAudioResponse,
)
from decime_api.services.ai.ai_power_state import is_stt_powered_on, is_tts_powered_on
from decime_api.services.ai.speech_provider import STTProvider, TTSProvider
from decime_api.services.audio.audio_service import (
    begin_synthesize_job,
    get_synthesize_job,
    run_synthesize_job,
    transcribe_upload,
)
from decime_api.services.http_errors import raise_upstream_error
from decime_api.services.storage.audio_storage import LocalAudioStorage

router = APIRouter(prefix="/audio", tags=["audio"])

# Keep in sync with deploy reverse-proxy upload limits (~25 MiB).
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post("/transcribe", response_model=TranscribeAudioResponse)
async def transcribe_audio(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    language_hint: str = Form(default="auto"),
    source_type: str = Form(default="user_voice"),
    stt: STTProvider = Depends(get_stt_provider),
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> TranscribeAudioResponse:
    if not is_stt_powered_on():
        raise HTTPException(status_code=503, detail="STT is powered off")
    user_id = resolve_user_id(user)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25 MB)")
    try:
        return await transcribe_upload(
            user_id=user_id,
            file_bytes=data,
            filename=file.filename or "audio.webm",
            mime_type=file.content_type or "application/octet-stream",
            language_hint=language_hint,
            source_type=source_type,
            stt=stt,
            storage=storage,
        )
    except Exception as error:  # noqa: BLE001 — provider errors vary; client gets a generic 502
        from decime_api.services.analytics.event_log import EVENT_ERROR_OCCURRED, log_event

        await log_event(user_id, EVENT_ERROR_OCCURRED, {"route": "audio/transcribe", "error": str(error)})
        raise_upstream_error("audio/transcribe", error)


@router.post("/synthesize", response_model=SynthesizeAudioResponse)
async def synthesize_audio(
    request: SynthesizeAudioRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    tts: TTSProvider = Depends(get_tts_provider),
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> SynthesizeAudioResponse:
    if not is_tts_powered_on():
        raise HTTPException(status_code=503, detail="TTS is powered off")
    user_id = resolve_user_id(user)
    try:
        started = await begin_synthesize_job(user_id, request, tts, storage)
    except RuntimeError as error:
        raise_upstream_error("audio/synthesize", error)
    if started.status == "pending" and started.job_id:
        background_tasks.add_task(run_synthesize_job, started.job_id, tts, storage)
    return started


@router.get("/synthesize/jobs/{job_id}", response_model=SynthesizeJobStatusResponse)
async def synthesize_job_status(
    job_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> SynthesizeJobStatusResponse:
    if not is_tts_powered_on():
        raise HTTPException(status_code=503, detail="TTS is powered off")
    user_id = resolve_user_id(user)
    job = get_synthesize_job(job_id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="TTS job not found")
    return job


@router.get("/files/{audio_id}")
async def get_audio_file(
    audio_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    storage: LocalAudioStorage = Depends(get_audio_storage),
) -> FileResponse:
    user_id = resolve_user_id(user)
    stored = storage.get(audio_id, user_id=user_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path=stored.storage_path, media_type=stored.mime_type)
