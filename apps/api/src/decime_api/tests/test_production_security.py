import pytest

from decime_api.config import Settings


def test_production_security_rejects_weak_jwt() -> None:
    settings = Settings(
        app_env="production",
        auth_enabled=True,
        auth_jwt_secret="short",
        frontend_base_url="https://decime.online",
        api_base_url="https://api.decime.online",
        auth_allow_registration=False,
    )
    with pytest.raises(ValueError, match="32 characters"):
        settings.validate_production_security()


def test_production_security_rejects_open_registration() -> None:
    settings = Settings(
        app_env="production",
        auth_enabled=True,
        auth_jwt_secret="a" * 32,
        frontend_base_url="https://decime.online",
        api_base_url="https://api.decime.online",
        auth_allow_registration=True,
    )
    with pytest.raises(ValueError, match="AUTH_ALLOW_REGISTRATION"):
        settings.validate_production_security()


def test_production_cors_only_web_origins() -> None:
    settings = Settings(
        app_env="production",
        frontend_base_url="https://decime.online",
    )
    origins = settings.cors_allowed_origins()
    assert "https://decime.online" in origins
    assert "https://www.decime.online" in origins
    assert "http://localhost:3000" not in origins
    assert "capacitor://localhost" in origins


def test_local_cors_wildcard() -> None:
    settings = Settings(app_env="local")
    assert settings.cors_allowed_origins() == ["*"]


def test_local_keeps_openapi_docs_enabled() -> None:
    from decime_api.main import app

    # Default test / local app keeps interactive docs for developers.
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"
