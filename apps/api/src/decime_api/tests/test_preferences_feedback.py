from fastapi.testclient import TestClient


def _register(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_app_language_preferences(auth_client: TestClient) -> None:
    token = _register(auth_client, "lang@example.com")
    me = auth_client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json().get("app_language") is None

    updated = auth_client.patch(
        "/api/v1/auth/me/preferences",
        headers=_auth(token),
        json={"app_language": "en"},
    )
    assert updated.status_code == 200
    assert updated.json()["app_language"] == "en"

    again = auth_client.get("/api/v1/auth/me", headers=_auth(token))
    assert again.json()["app_language"] == "en"


def test_translation_rating_and_admin_dashboard(auth_client: TestClient) -> None:
    token = _register(auth_client, "rate-user@example.com")
    rated = auth_client.post(
        "/api/v1/feedback/translation-rating",
        headers=_auth(token),
        json={
            "feature": "quick_reply",
            "rating": 1,
            "source_text": "hola",
            "result_text": "привет",
            "direction": "to_explanation",
        },
    )
    assert rated.status_code == 200
    assert rated.json()["rating"] == 1

    from decime_api.db.user_store import get_user_store

    user = get_user_store().get_by_email("rate-user@example.com")
    assert user is not None
    get_user_store().update_user(user.id, role="admin")

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "rate-user@example.com", "password": "password123"},
    )
    admin_token = login.json()["access_token"]
    dashboard = auth_client.get(
        "/api/v1/admin/dashboard?days=30",
        headers=_auth(admin_token),
    )
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "usage" in body and "ratings" in body
    assert body["ratings"]["total"] >= 1
