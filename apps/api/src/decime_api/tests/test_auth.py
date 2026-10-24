from fastapi.testclient import TestClient


def test_auth_config(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/auth/config")
    assert response.status_code == 200
    assert response.json()["auth_enabled"] is True


def test_register_login_and_me(auth_client: TestClient) -> None:
    register = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "secretpass", "display_name": "Test"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]

    me = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secretpass"},
    )
    assert login.status_code == 200

    protected = auth_client.post(
        "/api/v1/incoming/understand-text",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "source_text": "Hola",
            "source_language": "es",
            "target_language": "ru",
            "locale_variant": "es-UY-montevideo",
            "channel": "whatsapp_text",
        },
    )
    assert protected.status_code == 200


def test_protected_route_without_token(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/incoming/understand-text",
        json={
            "source_text": "Hola",
            "source_language": "es",
            "target_language": "ru",
            "locale_variant": "es-UY-montevideo",
            "channel": "whatsapp_text",
        },
    )
    assert response.status_code == 401


def test_admin_create_user(auth_client: TestClient) -> None:
    admin = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "adminpass1", "display_name": "Admin"},
    )
    assert admin.status_code == 201

    from decime_api.db.user_store import get_user_store

    user = get_user_store().get_by_email("admin@example.com")
    assert user is not None
    get_user_store().update_user(user.id, role="admin")

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass1"},
    )
    admin_token = login.json()["access_token"]

    created = auth_client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "member@example.com",
            "password": "memberpass",
            "display_name": "Member",
            "role": "user",
        },
    )
    assert created.status_code == 201
    assert created.json()["email"] == "member@example.com"

    listing = auth_client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert listing.status_code == 200
    assert len(listing.json()) >= 2
