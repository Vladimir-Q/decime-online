"""Admin STT/TTS power orchestration (enable + warm / disable + unload|stop)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from decime_api.config import settings
from decime_api.dependencies import get_stt_provider
from decime_api.services.ai.ai_power_state import (
    AiPowerState,
    load_ai_power_state,
    save_ai_power_state,
)
from decime_api.services.ai.docker_ai_control import DockerAiControlError, DockerAiController
from decime_api.services.ai.faster_whisper_stt import FasterWhisperSTTProvider
from decime_api.services.ai.openai_speech import OpenAISTTProvider

logger = logging.getLogger(__name__)


def get_docker_controller() -> DockerAiController:
    return DockerAiController()


def _edge_speech_mode() -> bool:
    """TTS/STT pointed off-VM (Tailscale PC) — no Docker start/stop on the API host."""
    if settings.openai_stt_base_url:
        return True
    orpheus = (settings.orpheus_tts_base_url or "").rstrip("/")
    # e.g. http://100.x.x.x:5005
    return bool(
        orpheus
        and "orpheus:" not in orpheus
        and "localhost" not in orpheus
        and "127.0.0.1" not in orpheus
    )


async def _probe_url(url: str, timeout: float = 5.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
        return response.status_code < 500
    except Exception:  # noqa: BLE001
        return False


async def _warm_remote_orpheus() -> None:
    """Ping edge Orpheus + optionally warm Ollama on the PC."""
    orpheus = settings.orpheus_tts_base_url.rstrip("/")
    ollama = settings.ollama_base_url.rstrip("/")
    if not await _probe_url(f"{orpheus}/docs") and not await _probe_url(f"{orpheus}/health"):
        # Orpheus-FastAPI always serves /docs when up
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.get(f"{orpheus}/docs")
            except Exception as error:
                raise RuntimeError(
                    f"Edge Orpheus not reachable at {orpheus}. "
                    "Is Tailscale up and Orpheus running on your PC?"
                ) from error

    # Best-effort model warm on edge Ollama (may take a while).
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{ollama}/api/generate",
                json={
                    "model": settings.orpheus_ollama_model,
                    "prompt": " ",
                    "stream": False,
                    "keep_alive": -1,
                },
            )
        if response.status_code >= 400:
            logger.warning("edge ollama warm HTTP %s: %s", response.status_code, response.text[:200])
    except Exception as error:  # noqa: BLE001
        logger.warning("edge ollama warm skipped: %s", error)


async def _warm_remote_stt() -> None:
    base = (settings.openai_stt_base_url or "").rstrip("/")
    if not base:
        return
    # Our edge whisper server exposes GET /health
    root = base.removesuffix("/v1")
    ok = await _probe_url(f"{root}/health") or await _probe_url(f"{base}/models")
    if not ok:
        raise RuntimeError(
            f"Edge Whisper STT not reachable at {base}. "
            "Start scripts/edge/whisper_server on your PC (Tailscale)."
        )


async def build_ai_power_status() -> dict[str, Any]:
    state = load_ai_power_state()
    docker = get_docker_controller()
    containers: dict[str, str] = {}
    docker_available = docker.available
    edge = _edge_speech_mode()
    if docker_available and not edge:
        try:
            containers = await docker.container_states()
        except DockerAiControlError as error:
            containers = {"error": str(error)}

    stt = get_stt_provider()
    stt_warm = False
    if isinstance(stt, FasterWhisperSTTProvider):
        stt_warm = stt.is_warm()
    elif state.stt_enabled:
        stt_warm = True

    tts_containers_running = bool(containers) and all(
        containers.get(name) == "running" for name in ("ollama", "orpheus")
    )

    return {
        "stt_enabled": state.stt_enabled,
        "tts_enabled": state.tts_enabled,
        "stt_status": state.stt_status,
        "tts_status": state.tts_status,
        "stt_warm": stt_warm,
        "tts_containers": containers,
        "tts_containers_running": tts_containers_running or (edge and state.tts_enabled),
        "docker_control_enabled": settings.ai_docker_control_enabled,
        "docker_control_available": docker_available and not edge,
        "edge_speech": edge,
        "orpheus_tts_base_url": settings.orpheus_tts_base_url,
        "openai_stt_base_url": settings.openai_stt_base_url,
        "stt_provider": settings.stt_provider,
        "tts_provider": settings.tts_provider or settings.speech_provider or "fake",
        "last_error": state.last_error,
    }


async def set_stt_powered(enabled: bool) -> dict[str, Any]:
    state = load_ai_power_state()
    state.last_error = None
    stt = get_stt_provider()

    if enabled:
        state.stt_status = "warming"
        save_ai_power_state(state)
        try:
            if isinstance(stt, FasterWhisperSTTProvider):
                await stt.warm()
            elif isinstance(stt, OpenAISTTProvider) and settings.openai_stt_base_url:
                await _warm_remote_stt()
            state.stt_enabled = True
            state.stt_status = "ready"
        except Exception as error:
            state.stt_enabled = False
            state.stt_status = "error"
            state.last_error = str(error)
            save_ai_power_state(state)
            raise
    else:
        if isinstance(stt, FasterWhisperSTTProvider):
            stt.unload()
        state.stt_enabled = False
        state.stt_status = "off"

    save_ai_power_state(state)
    return await build_ai_power_status()


async def set_tts_powered(enabled: bool) -> dict[str, Any]:
    state = load_ai_power_state()
    state.last_error = None
    docker = get_docker_controller()
    provider = settings.tts_provider or settings.speech_provider or "fake"
    needs_orpheus = provider == "orpheus"
    edge = _edge_speech_mode()

    if enabled:
        state.tts_status = "starting"
        save_ai_power_state(state)
        try:
            if needs_orpheus and edge:
                state.tts_status = "warming"
                save_ai_power_state(state)
                await _warm_remote_orpheus()
            elif needs_orpheus:
                if not docker.available:
                    raise DockerAiControlError(
                        "Docker AI control is not available. "
                        "For a home PC, set ORPHEUS_TTS_BASE_URL to your Tailscale IP "
                        "(edge mode) or enable AI_DOCKER_CONTROL_ENABLED on the VM."
                    )
                await docker.start_tts_stack()
                state.tts_status = "warming"
                save_ai_power_state(state)
                await docker.warm_ollama_model()
            state.tts_enabled = True
            state.tts_status = "ready"
        except Exception as error:
            state.tts_enabled = False
            state.tts_status = "error"
            state.last_error = str(error)
            save_ai_power_state(state)
            raise
    else:
        state.tts_status = "stopping"
        save_ai_power_state(state)
        try:
            if needs_orpheus and edge:
                # PC processes stay up; API just refuses synthesize until powered on again.
                pass
            elif needs_orpheus and docker.available:
                await docker.stop_tts_stack()
            elif needs_orpheus and not docker.available:
                # No VM containers to stop (edge misdetect or docker control off).
                logger.info("TTS power off: docker control unavailable — flag only")
            state.tts_enabled = False
            state.tts_status = "off"
        except Exception as error:
            state.tts_status = "error"
            state.last_error = str(error)
            save_ai_power_state(state)
            raise

    save_ai_power_state(state)
    return await build_ai_power_status()


async def reconcile_tts_on_startup() -> None:
    """If TTS is powered off, stop VM containers (skip in edge/Tailscale mode)."""
    state = load_ai_power_state()
    if state.tts_enabled:
        return
    if _edge_speech_mode():
        return
    provider = settings.tts_provider or settings.speech_provider or "fake"
    if provider != "orpheus":
        return
    docker = get_docker_controller()
    if not docker.available:
        return
    try:
        await docker.stop_tts_stack()
        state.tts_status = "off"
        state.last_error = None
        save_ai_power_state(state)
        logger.info("reconcile: TTS powered off — stopped ollama/orpheus")
    except DockerAiControlError as error:
        logger.warning("reconcile TTS stop failed: %s", error)


def ensure_default_power_file() -> AiPowerState:
    return load_ai_power_state()
