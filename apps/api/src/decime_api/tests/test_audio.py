import pytest
from fastapi.testclient import TestClient

from decime_api.dependencies import reset_audio_storage
from decime_api.main import app


@pytest.fixture
def audio_client(client: TestClient, tmp_path) -> TestClient:
    from decime_api.dependencies import get_audio_storage
    from decime_api.services.storage.audio_storage import LocalAudioStorage

    reset_audio_storage()
    storage = LocalAudioStorage(tmp_path / "audio")
    app.dependency_overrides[get_audio_storage] = lambda: storage
    yield client
    app.dependency_overrides.pop(get_audio_storage, None)
    reset_audio_storage()


def test_transcribe_audio_fake(audio_client: TestClient) -> None:
    response = audio_client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("factura.webm", b"fake-audio", "audio/webm")},
        data={"language_hint": "es", "source_type": "whatsapp_audio"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "factura" in data["transcript"].lower()
    assert data["audio_id"]


def test_synthesize_audio_fake(audio_client: TestClient) -> None:
    response = audio_client.post(
        "/api/v1/audio/synthesize",
        json={
            "text": "Hola, quería consultar si se puede pagar con tarjeta.",
            "locale": "es-UY-montevideo",
            "mode": "reply",
            "speed": "normal",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["audio_id"]
    assert data["cached"] is False
    assert data.get("status", "ready") == "ready"

    file_response = audio_client.get(f"/api/v1/audio/files/{data['audio_id']}")
    assert file_response.status_code == 200

    cached_response = audio_client.post(
        "/api/v1/audio/synthesize",
        json={
            "text": "Hola, quería consultar si se puede pagar con tarjeta.",
            "locale": "es-UY-montevideo",
            "mode": "reply",
            "speed": "normal",
        },
    )
    assert cached_response.json()["cached"] is True


def test_clear_history_and_audio(audio_client: TestClient) -> None:
    audio_client.post(
        "/api/v1/translate/text",
        json={"source_text": "Я хочу уточнить, можно ли оплатить картой."},
    )
    audio_client.post(
        "/api/v1/audio/synthesize",
        json={"text": "Hola", "locale": "es-UY-montevideo"},
    )

    clear_response = audio_client.delete("/api/v1/history")
    assert clear_response.status_code == 200

    history = audio_client.get("/api/v1/history").json()
    assert history["total"] == 0
