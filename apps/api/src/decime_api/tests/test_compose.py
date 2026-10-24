def test_translate_to_esuy_endpoint(client) -> None:
    payload = {
        "source_language": "ru",
        "source_text": "Я хочу уточнить, можно ли оплатить картой.",
        "context": {
            "channel": "whatsapp_text",
            "user_level": "A2",
        },
    }
    response = client.post("/api/v1/translate/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"]
    assert "tarjeta" in data["recommended_reply"]
    assert "simple_reply" not in data
    assert "Montevideo" in data["dialect_stamp"] or "es-UY" in data["dialect_stamp"]


def test_translate_recommended_any_level(client) -> None:
    payload = {
        "source_language": "ru",
        "source_text": "Я хочу уточнить, можно ли оплатить картой.",
        "context": {"channel": "whatsapp_text", "user_level": None},
    }
    response = client.post("/api/v1/translate/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "tarjeta" in data["recommended_reply"]
    assert "any-friendly" in data["dialect_stamp"]


def test_history_lists_compose_results(client) -> None:
    payload = {
        "source_text": "Я хочу уточнить, можно ли оплатить картой.",
        "context": {"channel": "whatsapp_text"},
    }
    compose_response = client.post("/api/v1/translate/text", json=payload)
    request_id = compose_response.json()["request_id"]

    history_response = client.get("/api/v1/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["total"] >= 1
    assert any(item["request_id"] == request_id for item in history["items"])
