from fastapi.testclient import TestClient

from decime_api.db.training import reset_training_repository


def _default_list_id(client: TestClient) -> str:
    lists = client.get("/api/v1/training/lists")
    assert lists.status_code == 200
    return lists.json()[0]["list_id"]


def _approve_sample_items(client: TestClient, *, generate_audio: bool = False) -> str:
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
    response = client.post(
        "/api/v1/training/approve-candidates",
        json={
            "list_id": list_id,
            "extraction_id": extract["extraction_id"],
            "approved_candidate_ids": candidate_ids,
            "generate_audio": generate_audio,
        },
    )
    assert response.status_code == 200
    return list_id


def test_review_next_returns_due_items(client: TestClient) -> None:
    reset_training_repository()
    list_id = _approve_sample_items(client)

    response = client.get(f"/api/v1/training/review/next?list_id={list_id}&limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["due_count"] >= 2
    assert len(payload["items"]) >= 2
    item = payload["items"][0]
    assert item["item_id"]
    assert item["display_text"]
    assert "ru_to_es" in item["review_modes"]
    assert "es_to_ru" in item["review_modes"]
    assert "grammar_prompt" in item["review_modes"]


def test_review_submit_updates_schedule(client: TestClient) -> None:
    reset_training_repository()
    list_id = _approve_sample_items(client)

    queue = client.get(f"/api/v1/training/review/next?list_id={list_id}&limit=1").json()
    item = queue["items"][0]

    submit = client.post(
        "/api/v1/training/review/submit",
        json={
            "item_id": item["item_id"],
            "review_mode": "ru_to_es",
            "grade": "good",
            "response_latency_ms": 1200,
            "used_hint": False,
        },
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["review_stage"] == 1
    assert body["next_review_at"]
    assert body["remaining_due"] >= 1

    items = client.get(f"/api/v1/training/items?list_id={list_id}").json()["items"]
    reviewed = next(row for row in items if row["item_id"] == item["item_id"])
    assert reviewed["review_stage"] == 1


def test_review_submit_again_keeps_item_due(client: TestClient) -> None:
    reset_training_repository()
    list_id = _approve_sample_items(client, generate_audio=True)

    queue = client.get(f"/api/v1/training/review/next?list_id={list_id}&limit=1").json()
    item = queue["items"][0]
    assert "audio_to_meaning" in item["review_modes"]
    assert item["audio_url"]

    submit = client.post(
        "/api/v1/training/review/submit",
        json={
            "item_id": item["item_id"],
            "review_mode": "audio_to_meaning",
            "grade": "again",
            "response_latency_ms": 800,
            "used_hint": True,
        },
    )
    assert submit.status_code == 200
    assert submit.json()["review_stage"] == 0


def test_lists_include_due_count(client: TestClient) -> None:
    reset_training_repository()
    _approve_sample_items(client)

    lists = client.get("/api/v1/training/lists").json()
    assert lists[0]["due_count"] >= 2
