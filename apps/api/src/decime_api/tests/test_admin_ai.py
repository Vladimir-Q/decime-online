from fastapi.testclient import TestClient

from decime_api.db.user_store import get_user_store
from decime_api.services.ai.ai_power_state import AiPowerState, save_ai_power_state


def _register(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(client: TestClient, email: str, password: str = "password123") -> str:
    _register(client, email, password)
    user = get_user_store().get_by_email(email)
    assert user is not None
    get_user_store().update_user(user.id, role="admin")
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_admin_ai_status_requires_admin(auth_client: TestClient) -> None:
    token = _register(auth_client, "user@example.com")
    response = auth_client.get("/api/v1/admin/ai/status", headers=_auth(token))
    assert response.status_code == 403


def test_admin_ai_stt_toggle_and_audio_gate(auth_client: TestClient) -> None:
    token = _admin_token(auth_client, "admin-ai@example.com")

    status = auth_client.get("/api/v1/admin/ai/status", headers=_auth(token))
    assert status.status_code == 200
    assert status.json()["stt_enabled"] is True

    off = auth_client.post(
        "/api/v1/admin/ai/stt",
        headers=_auth(token),
        json={"enabled": False},
    )
    assert off.status_code == 200
    assert off.json()["stt_enabled"] is False
    assert off.json()["stt_status"] == "off"

    blocked = auth_client.post(
        "/api/v1/audio/transcribe",
        headers=_auth(token),
        files={"file": ("clip.webm", b"fake-audio", "audio/webm")},
        data={"language_hint": "es", "source_type": "user_voice"},
    )
    assert blocked.status_code == 503
    assert "powered off" in blocked.json()["detail"].lower()

    on = auth_client.post(
        "/api/v1/admin/ai/stt",
        headers=_auth(token),
        json={"enabled": True},
    )
    assert on.status_code == 200
    assert on.json()["stt_enabled"] is True

    ok = auth_client.post(
        "/api/v1/audio/transcribe",
        headers=_auth(token),
        files={"file": ("clip.webm", b"fake-audio", "audio/webm")},
        data={"language_hint": "es", "source_type": "user_voice"},
    )
    assert ok.status_code == 200


def test_admin_ai_tts_toggle_and_audio_gate(auth_client: TestClient) -> None:
    token = _admin_token(auth_client, "admin-tts@example.com")

    off = auth_client.post(
        "/api/v1/admin/ai/tts",
        headers=_auth(token),
        json={"enabled": False},
    )
    assert off.status_code == 200
    assert off.json()["tts_enabled"] is False

    blocked = auth_client.post(
        "/api/v1/audio/synthesize",
        headers=_auth(token),
        json={"text": "Hola", "locale": "es-UY-montevideo"},
    )
    assert blocked.status_code == 503
    assert "powered off" in blocked.json()["detail"].lower()

    on = auth_client.post(
        "/api/v1/admin/ai/tts",
        headers=_auth(token),
        json={"enabled": True},
    )
    assert on.status_code == 200
    assert on.json()["tts_enabled"] is True

    ok = auth_client.post(
        "/api/v1/audio/synthesize",
        headers=_auth(token),
        json={"text": "Hola", "locale": "es-UY-montevideo"},
    )
    assert ok.status_code == 200


def test_audio_gate_without_admin_toggle(client: TestClient) -> None:
    save_ai_power_state(
        AiPowerState(stt_enabled=False, tts_enabled=False, stt_status="off", tts_status="off")
    )
    stt = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("clip.webm", b"fake-audio", "audio/webm")},
        data={"language_hint": "es", "source_type": "user_voice"},
    )
    assert stt.status_code == 503
    tts = client.post(
        "/api/v1/audio/synthesize",
        json={"text": "Hola", "locale": "es-UY-montevideo"},
    )
    assert tts.status_code == 503


def test_admin_ai_edge_mode_status_and_power(auth_client: TestClient, monkeypatch) -> None:
    """Edge Tailscale URLs: status reports edge_speech; power on probes remotes, not Docker."""
    from decime_api.config import settings as live_settings
    from decime_api.services.ai import ai_power_service
    from decime_api.services.ai.openai_speech import OpenAISTTProvider

    live_settings.openai_stt_base_url = "http://100.64.0.10:8090/v1"
    live_settings.orpheus_tts_base_url = "http://100.64.0.10:5005"
    live_settings.ollama_base_url = "http://100.64.0.10:11434"
    live_settings.orpheus_ollama_model = "sematre/orpheus:it_es"
    live_settings.stt_provider = "openai"
    live_settings.tts_provider = "orpheus"
    live_settings.ai_docker_control_enabled = False

    edge_stt = OpenAISTTProvider("sk-local", "whisper-base", base_url=live_settings.openai_stt_base_url)
    monkeypatch.setattr(ai_power_service, "get_stt_provider", lambda: edge_stt)

    warm_stt_calls: list[bool] = []
    warm_tts_calls: list[bool] = []

    async def fake_warm_stt() -> None:
        warm_stt_calls.append(True)

    async def fake_warm_orpheus() -> None:
        warm_tts_calls.append(True)

    class BoomDocker:
        available = True

        async def start_tts_stack(self) -> None:
            raise AssertionError("Docker start must not run in edge mode")

        async def stop_tts_stack(self) -> None:
            raise AssertionError("Docker stop must not run in edge mode")

        async def warm_ollama_model(self) -> None:
            raise AssertionError("Docker warm must not run in edge mode")

        async def container_states(self) -> dict[str, str]:
            raise AssertionError("Docker container_states must not run in edge mode")

    monkeypatch.setattr(ai_power_service, "_warm_remote_stt", fake_warm_stt)
    monkeypatch.setattr(ai_power_service, "_warm_remote_orpheus", fake_warm_orpheus)
    monkeypatch.setattr(ai_power_service, "get_docker_controller", lambda: BoomDocker())

    token = _admin_token(auth_client, "admin-edge@example.com")
    headers = _auth(token)

    status = auth_client.get("/api/v1/admin/ai/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["edge_speech"] is True
    assert body["docker_control_available"] is False
    assert body["openai_stt_base_url"] == "http://100.64.0.10:8090/v1"
    assert body["orpheus_tts_base_url"] == "http://100.64.0.10:5005"

    save_ai_power_state(
        AiPowerState(stt_enabled=False, tts_enabled=False, stt_status="off", tts_status="off")
    )

    stt_on = auth_client.post(
        "/api/v1/admin/ai/stt",
        headers=headers,
        json={"enabled": True},
    )
    assert stt_on.status_code == 200, stt_on.text
    assert stt_on.json()["stt_enabled"] is True
    assert stt_on.json()["edge_speech"] is True
    assert warm_stt_calls == [True]

    tts_on = auth_client.post(
        "/api/v1/admin/ai/tts",
        headers=headers,
        json={"enabled": True},
    )
    assert tts_on.status_code == 200, tts_on.text
    assert tts_on.json()["tts_enabled"] is True
    assert warm_tts_calls == [True]

    tts_off = auth_client.post(
        "/api/v1/admin/ai/tts",
        headers=headers,
        json={"enabled": False},
    )
    assert tts_off.status_code == 200, tts_off.text
    assert tts_off.json()["tts_enabled"] is False
    assert tts_off.json()["tts_status"] == "off"
