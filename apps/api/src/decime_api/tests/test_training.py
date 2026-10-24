from fastapi.testclient import TestClient

from decime_api.db.training import reset_training_repository


def _default_list_id(client: TestClient) -> str:
    lists = client.get("/api/v1/training/lists")
    assert lists.status_code == 200
    return lists.json()[0]["list_id"]


def test_extract_candidates_fake(client: TestClient) -> None:
    reset_training_repository()
    response = client.post(
        "/api/v1/training/extract-candidates",
        json={
            "source_type": "generated_reply",
            "source_language": "ru",
            "source_original_text": "Можно ли картой?",
            "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
            "target_locale": "es-UY-montevideo",
            "user_level": "A2",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["extraction_id"]
    assert len(payload["candidates"]) >= 2
    assert any(item["item_type"] == "noun" for item in payload["candidates"])


def test_approve_candidates(client: TestClient) -> None:
    reset_training_repository()
    list_id = _default_list_id(client)
    extract = client.post(
        "/api/v1/training/extract-candidates",
        json={
            "source_type": "generated_reply",
            "source_language": "ru",
            "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
        },
    ).json()

    candidate_ids = [item["candidate_id"] for item in extract["candidates"][:2]]
    approve = client.post(
        "/api/v1/training/approve-candidates",
        json={
            "list_id": list_id,
            "extraction_id": extract["extraction_id"],
            "approved_candidate_ids": candidate_ids,
            "generate_audio": True,
        },
    )
    assert approve.status_code == 200
    created = approve.json()["created_items"]
    assert len(created) == 2
    assert created[0]["audio_status"] == "ready"

    items = client.get(f"/api/v1/training/items?list_id={list_id}")
    assert items.status_code == 200
    assert len(items.json()["items"]) == 2


def test_approve_skips_duplicates(client: TestClient) -> None:
    reset_training_repository()
    list_id = _default_list_id(client)
    extract = client.post(
        "/api/v1/training/extract-candidates",
        json={
            "source_type": "generated_reply",
            "source_language": "ru",
            "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
        },
    ).json()
    candidate_id = extract["candidates"][0]["candidate_id"]

    first = client.post(
        "/api/v1/training/approve-candidates",
        json={
            "list_id": list_id,
            "extraction_id": extract["extraction_id"],
            "approved_candidate_ids": [candidate_id],
            "generate_audio": False,
        },
    )
    assert first.status_code == 200

    extract_again = client.post(
        "/api/v1/training/extract-candidates",
        json={
            "source_type": "generated_reply",
            "source_language": "ru",
            "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
        },
    ).json()
    duplicates = [
        item for item in extract_again["candidates"] if item["status_hint"] == "duplicate_possible"
    ]
    assert duplicates

    second = client.post(
        "/api/v1/training/approve-candidates",
        json={
            "list_id": list_id,
            "extraction_id": extract_again["extraction_id"],
            "approved_candidate_ids": [duplicates[0]["candidate_id"]],
            "generate_audio": False,
        },
    )
    assert second.status_code == 200
    assert len(second.json()["created_items"]) == 0
    assert second.json()["skipped_duplicates"]
