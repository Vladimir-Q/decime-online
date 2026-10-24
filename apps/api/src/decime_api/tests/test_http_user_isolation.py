"""HTTP-level isolation: training / history / audio must not leak across users."""

from __future__ import annotations

from fastapi.testclient import TestClient

from decime_api.dependencies import (
    get_audio_storage,
    get_history_repository,
    get_training_extractor,
    get_tts_provider,
)
from decime_api.main import app
from decime_api.services.ai.fake_speech import FakeTTSProvider
from decime_api.services.ai.fake_training_extractor import FakeTrainingExtractor
from decime_api.services.compose.reply_composer import MemoryHistoryRepository
from decime_api.services.storage.audio_storage import LocalAudioStorage


def _register(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_training_history_audio_isolated_between_users(auth_client: TestClient, tmp_path) -> None:
    storage = LocalAudioStorage(tmp_path / "audio")
    history = MemoryHistoryRepository()
    app.dependency_overrides[get_audio_storage] = lambda: storage
    app.dependency_overrides[get_history_repository] = lambda: history
    app.dependency_overrides[get_training_extractor] = lambda: FakeTrainingExtractor()
    app.dependency_overrides[get_tts_provider] = lambda: FakeTTSProvider()

    token_a = _register(auth_client, "iso-a@example.com", "passwordA1")
    token_b = _register(auth_client, "iso-b@example.com", "passwordB1")

    # User A: compose history + training + audio
    compose_a = auth_client.post(
        "/api/v1/translate/text",
        headers=_auth(token_a),
        json={"source_text": "Хочу спросить про карту."},
    )
    assert compose_a.status_code == 200, compose_a.text

    lists_a = auth_client.get("/api/v1/training/lists", headers=_auth(token_a))
    assert lists_a.status_code == 200
    list_a = lists_a.json()[0]["list_id"]

    extract_a = auth_client.post(
        "/api/v1/training/extract-candidates",
        headers=_auth(token_a),
        json={
            "source_type": "generated_reply",
            "source_language": "ru",
            "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
            "list_id": list_a,
        },
    )
    assert extract_a.status_code == 200, extract_a.text
    extraction = extract_a.json()
    candidate_ids = [
        c["candidate_id"]
        for c in extraction["candidates"]
        if c.get("status_hint") != "duplicate_possible"
    ][:1]
    assert candidate_ids

    approve_a = auth_client.post(
        "/api/v1/training/approve-candidates",
        headers=_auth(token_a),
        json={
            "list_id": list_a,
            "extraction_id": extraction["extraction_id"],
            "approved_candidate_ids": candidate_ids,
            "generate_audio": False,
        },
    )
    assert approve_a.status_code == 200, approve_a.text
    created = approve_a.json().get("created_items") or []
    assert created
    item_a_id = created[0]["item_id"]

    synth_a = auth_client.post(
        "/api/v1/audio/synthesize",
        headers=_auth(token_a),
        json={"text": "Hola desde A", "locale": "es-UY-montevideo"},
    )
    assert synth_a.status_code == 200, synth_a.text
    audio_a = synth_a.json()["audio_id"]

    # User B must not see A's history / list items / audio
    history_b = auth_client.get("/api/v1/history?limit=20", headers=_auth(token_b))
    assert history_b.status_code == 200
    assert history_b.json()["total"] == 0

    items_b_on_a_list = auth_client.get(
        f"/api/v1/training/items?list_id={list_a}",
        headers=_auth(token_b),
    )
    # Foreign list_id should not leak items (ownership assert → empty or error)
    assert items_b_on_a_list.status_code in (200, 403, 404)
    if items_b_on_a_list.status_code == 200:
        assert items_b_on_a_list.json().get("items") == []

    lists_b = auth_client.get("/api/v1/training/lists", headers=_auth(token_b))
    assert lists_b.status_code == 200
    list_b = lists_b.json()[0]["list_id"]
    assert list_b != list_a

    items_b = auth_client.get(
        f"/api/v1/training/items?list_id={list_b}",
        headers=_auth(token_b),
    )
    assert items_b.status_code == 200
    assert items_b.json().get("items") == []

    audio_b = auth_client.get(f"/api/v1/audio/files/{audio_a}", headers=_auth(token_b))
    assert audio_b.status_code == 404

    # User A still sees own data
    history_a = auth_client.get("/api/v1/history?limit=20", headers=_auth(token_a))
    assert history_a.status_code == 200
    assert history_a.json()["total"] >= 1

    items_a = auth_client.get(
        f"/api/v1/training/items?list_id={list_a}",
        headers=_auth(token_a),
    )
    assert items_a.status_code == 200
    ids = {item["item_id"] for item in items_a.json()["items"]}
    assert item_a_id in ids

    audio_ok = auth_client.get(f"/api/v1/audio/files/{audio_a}", headers=_auth(token_a))
    assert audio_ok.status_code == 200

    app.dependency_overrides.pop(get_audio_storage, None)
    app.dependency_overrides.pop(get_history_repository, None)
    app.dependency_overrides.pop(get_training_extractor, None)
    app.dependency_overrides.pop(get_tts_provider, None)
