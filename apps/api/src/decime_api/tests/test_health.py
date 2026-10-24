from fastapi.testclient import TestClient

from decime_api.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert data["app"] == "Decime UY"
    assert "env" in data
    assert "speech_ready" in data
    assert "stt_reachable" in data
    assert "tts_reachable" in data
