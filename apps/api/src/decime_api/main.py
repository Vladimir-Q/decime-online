from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from decime_api.auth.dependencies import get_current_user
from decime_api.config import settings
from decime_api.db.postgres import close_postgres, run_migrations
from decime_api.db.user_store import bootstrap_admin_if_configured, get_user_store
from decime_api.middleware.rate_limit import RateLimitMiddleware
from decime_api.routers import (
    admin_ai,
    audio,
    auth,
    feedback,
    history,
    incoming,
    integrations_n8n,
    training,
    translate,
)
from decime_api.services.ai.ai_power_service import (
    ensure_default_power_file,
    reconcile_tts_on_startup,
)
from decime_api.services.ai.lc.prompt_provider import prompt_health_fields
from decime_api.services.ai.lc.tracing import configure_langsmith_tracing, tracing_active

_OPENAPI = settings.openapi_enabled


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_production_security()
    configure_langsmith_tracing()
    from decime_api.services.ai.lc.prompt_provider import warm_prompt_cache

    warm_prompt_cache()
    if settings.use_postgres:
        settings.validate_postgres_auth()
        run_migrations()
    if settings.auth_enabled or settings.use_postgres:
        get_user_store().init_db()
        bootstrap_admin_if_configured()
    ensure_default_power_file()
    await reconcile_tts_on_startup()
    yield
    close_postgres()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Uruguayan Spanish Communication Copilot API",
    lifespan=lifespan,
    docs_url="/docs" if _OPENAPI else None,
    redoc_url="/redoc" if _OPENAPI else None,
    openapi_url="/openapi.json" if _OPENAPI else None,
)

_protected = [Depends(get_current_user)]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins(),
    allow_credentials=settings.app_env != "local",
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin_ai.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1", dependencies=_protected)
app.include_router(translate.router, prefix="/api/v1", dependencies=_protected)
app.include_router(incoming.router, prefix="/api/v1", dependencies=_protected)
app.include_router(history.router, prefix="/api/v1", dependencies=_protected)
app.include_router(audio.router, prefix="/api/v1", dependencies=_protected)
app.include_router(training.router, prefix="/api/v1", dependencies=_protected)
# n8n server-to-server routes use Header Auth, not user JWT.
app.include_router(integrations_n8n.router, prefix="/api/v1")


def _active_llm() -> tuple[str, str]:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return "openai", settings.openai_text_model
    return "fake", "fake-compose-v1"


@app.get("/health")
async def health() -> dict[str, str]:
    active_llm, llm_model = _active_llm()
    stt = settings.stt_provider
    tts = settings.tts_provider or settings.speech_provider or "fake"
    tts_model = _tts_model_label(tts)

    stt_ok, tts_ok = await _probe_speech_providers()
    speech_ready = "true" if stt_ok and tts_ok else "false"
    status = "ok" if stt_ok and tts_ok else "degraded"

    return {
        "status": status,
        "app": settings.app_name,
        "env": settings.app_env,
        "auth_enabled": str(settings.auth_enabled).lower(),
        "postgres_enabled": str(settings.use_postgres).lower(),
        "llm_provider": active_llm,
        "llm_model": llm_model,
        "llm_orchestrator": settings.llm_orchestrator,
        "llm_tracing": "true" if tracing_active() else "false",
        "stt_provider": stt,
        "stt_model": _stt_model_label(stt),
        "tts_provider": tts,
        "tts_model": tts_model,
        "openai_stt_base_url": settings.openai_stt_base_url or "",
        "orpheus_tts_base_url": settings.orpheus_tts_base_url,
        "stt_reachable": "true" if stt_ok else "false",
        "tts_reachable": "true" if tts_ok else "false",
        "speech_ready": speech_ready,
        **prompt_health_fields(),
    }


async def _probe_speech_providers() -> tuple[bool, bool]:
    """Best-effort reachability for configured STT/TTS (short timeouts)."""
    from decime_api.services.ai.ai_power_service import _probe_url

    stt_ok = True
    tts_ok = True

    stt_base = (settings.openai_stt_base_url or "").rstrip("/")
    if settings.stt_provider == "openai" and stt_base:
        root = stt_base.removesuffix("/v1")
        stt_ok = await _probe_url(f"{root}/health", timeout=1.5) or await _probe_url(
            f"{stt_base}/models",
            timeout=1.5,
        )

    if (settings.tts_provider or "").lower() == "orpheus":
        orpheus = settings.orpheus_tts_base_url.rstrip("/")
        tts_ok = await _probe_url(f"{orpheus}/docs", timeout=1.5) or await _probe_url(
            f"{orpheus}/health",
            timeout=1.5,
        )

    return stt_ok, tts_ok


def _tts_model_label(tts: str) -> str:
    if tts == "openai":
        return settings.openai_tts_model
    if tts == "orpheus":
        return f"{settings.orpheus_tts_model}/{settings.orpheus_tts_voice}"
    return "fake-tts-v1"


def _stt_model_label(stt: str) -> str:
    if stt == "openai":
        return settings.openai_stt_model
    if stt == "ollama":
        return settings.ollama_stt_model
    if stt in ("faster_whisper", "local"):
        return f"whisper-{settings.whisper_model_size}"
    return "fake-stt-v1"
