from pathlib import Path

from fastapi.testclient import TestClient

from decime_api.config import Settings
from decime_api.middleware.rate_limit import reset_rate_limit_state
from decime_api.services.storage.audio_storage import LocalAudioStorage, sanitize_audio_extension


def test_production_disables_openapi_flag() -> None:
    prod = Settings(
        app_env="production",
        auth_enabled=True,
        auth_jwt_secret="a" * 32,
        frontend_base_url="https://decime.online",
        api_base_url="https://api.decime.online",
        auth_allow_registration=False,
    )
    local = Settings(app_env="local")
    assert prod.openapi_enabled is False
    assert local.openapi_enabled is True


def test_sanitize_audio_extension_blocks_traversal() -> None:
    assert sanitize_audio_extension("webm") == "webm"
    assert sanitize_audio_extension("WAV") == "wav"
    assert sanitize_audio_extension("../evil") == "webm"
    assert sanitize_audio_extension("webm/../../x") == "webm"
    assert sanitize_audio_extension("exe") == "webm"


def test_audio_get_denies_missing_owner(tmp_path: Path) -> None:
    storage = LocalAudioStorage(tmp_path)
    stored = storage.save_bytes(
        b"abc",
        mime_type="audio/webm",
        extension="webm",
        user_id=None,
    )
    # Legacy null-owner record must not be readable under a scoped user_id.
    assert storage.get(stored.audio_id, user_id="user-a") is None
    assert storage.get(stored.audio_id, user_id=None) is not None


def test_audio_get_isolates_users(tmp_path: Path) -> None:
    storage = LocalAudioStorage(tmp_path)
    a = storage.save_bytes(b"a", mime_type="audio/webm", extension="webm", user_id="user-a")
    b = storage.save_bytes(b"b", mime_type="audio/webm", extension="webm", user_id="user-b")
    assert storage.get(a.audio_id, user_id="user-a") is not None
    assert storage.get(a.audio_id, user_id="user-b") is None
    assert storage.get(b.audio_id, user_id="user-a") is None


def test_audio_rejects_path_traversal_extension(tmp_path: Path) -> None:
    storage = LocalAudioStorage(tmp_path)
    stored = storage.save_bytes(
        b"safe",
        mime_type="audio/webm",
        extension="webm/../../evil",
        user_id="user-a",
    )
    assert stored.storage_path.parent.name == "user-a"
    assert stored.storage_path.suffix == ".webm"
    assert stored.storage_path.exists()


def test_login_rate_limit(auth_client: TestClient) -> None:
    reset_rate_limit_state()
    for _ in range(10):
        response = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
    limited = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-password"},
    )
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Too many requests. Try again later."
