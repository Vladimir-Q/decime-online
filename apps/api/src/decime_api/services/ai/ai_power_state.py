"""Persisted STT/TTS power flags (admin toggles)."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from decime_api.config import settings

_LOCK = threading.Lock()


@dataclass
class AiPowerState:
    stt_enabled: bool = True
    tts_enabled: bool = True
    stt_status: str = "ready"  # off | warming | ready | error
    tts_status: str = "ready"
    last_error: str | None = None


_STATE: AiPowerState | None = None


def ai_power_path() -> Path:
    # Persist on the audio volume (`/app/data/audio`), not the unmounted parent.
    return settings.audio_storage_path / "ai_power.json"


def load_ai_power_state() -> AiPowerState:
    global _STATE
    with _LOCK:
        if _STATE is not None:
            return _STATE
        path = ai_power_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                _STATE = AiPowerState(
                    stt_enabled=bool(raw.get("stt_enabled", True)),
                    tts_enabled=bool(raw.get("tts_enabled", True)),
                    stt_status=str(raw.get("stt_status", "ready" if raw.get("stt_enabled", True) else "off")),
                    tts_status=str(raw.get("tts_status", "ready" if raw.get("tts_enabled", True) else "off")),
                    last_error=raw.get("last_error"),
                )
                return _STATE
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        _STATE = AiPowerState()
        return _STATE


def save_ai_power_state(state: AiPowerState) -> AiPowerState:
    global _STATE
    with _LOCK:
        path = ai_power_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
        _STATE = state
        return _STATE


def reset_ai_power_state() -> None:
    """Tests only."""
    global _STATE
    with _LOCK:
        _STATE = None


def is_stt_powered_on() -> bool:
    return load_ai_power_state().stt_enabled


def is_tts_powered_on() -> bool:
    return load_ai_power_state().tts_enabled
