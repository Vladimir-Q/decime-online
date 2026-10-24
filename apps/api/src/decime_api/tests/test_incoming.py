from fastapi.testclient import TestClient


def test_understand_incoming_text_fake(client: TestClient) -> None:
    response = client.post(
        "/api/v1/incoming/understand-text",
        json={
            "source_text": "Podés pasar mañana después de las 10?",
            "source_language": "es",
            "target_language": "ru",
            "locale_variant": "es-UY-montevideo",
            "channel": "whatsapp_text",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["original_text"] == "Podés pasar mañana después de las 10?"
    assert payload["translation_ru"]
    assert "meaning_summary" not in payload
