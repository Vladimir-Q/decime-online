import pytest
from fastapi.testclient import TestClient

from decime_api.db.history import reset_history_repository
from decime_api.db.sheets_jobs import reset_sheets_job_repository
from decime_api.db.training import reset_training_repository
from decime_api.db.user_store import reset_user_store
from decime_api.dependencies import reset_audio_storage
from decime_api.main import app
from decime_api.middleware.rate_limit import reset_rate_limit_state
from decime_api.services.ai.ai_power_state import (
    AiPowerState,
    reset_ai_power_state,
    save_ai_power_state,
)
from decime_api.services.ai.fake_llm import FakeLLMProvider
from decime_api.services.ai.fake_speech import FakeSTTProvider, FakeTTSProvider
from decime_api.services.ai.fake_training_extractor import FakeTrainingExtractor
from decime_api.services.audio.audio_service import reset_synthesize_jobs
from decime_api.services.compose.reply_composer import MemoryHistoryRepository

# Opt-in markers: excluded from plain ``pytest`` so CI stays free/fast.
# Explicit ``pytest -m smoke_llm`` / ``pytest -m eval`` still works (markexpr set).
_DEFAULT_EXCLUDE_MARKERS = frozenset({"smoke_llm", "eval"})


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.option.markexpr:
        return
    items[:] = [
        item
        for item in items
        if _DEFAULT_EXCLUDE_MARKERS.isdisjoint(set(item.keywords))
    ]


@pytest.fixture
def client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("SPEECH_PROVIDER", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("AI_DOCKER_CONTROL_ENABLED", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from decime_api.config import settings as live_settings

    live_settings.auth_enabled = False
    live_settings.database_url = None
    live_settings.llm_provider = "fake"
    live_settings.stt_provider = "fake"
    live_settings.tts_provider = "fake"
    live_settings.ai_docker_control_enabled = False
    live_settings.audio_storage_dir = str(tmp_path / "audio")

    reset_history_repository()
    reset_training_repository()
    reset_sheets_job_repository()
    reset_user_store()
    reset_audio_storage()
    reset_ai_power_state()
    reset_synthesize_jobs()
    reset_rate_limit_state()
    save_ai_power_state(AiPowerState())
    memory_repo = MemoryHistoryRepository()

    from decime_api.dependencies import (
        get_history_repository,
        get_llm_provider,
        get_stt_provider,
        get_training_extractor,
        get_tts_provider,
    )

    app.dependency_overrides[get_history_repository] = lambda: memory_repo
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()
    app.dependency_overrides[get_training_extractor] = lambda: FakeTrainingExtractor()
    app.dependency_overrides[get_stt_provider] = lambda: FakeSTTProvider()
    app.dependency_overrides[get_tts_provider] = lambda: FakeTTSProvider()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_history_repository()
    reset_training_repository()
    reset_sheets_job_repository()
    reset_user_store()
    reset_audio_storage()
    reset_ai_power_state()


@pytest.fixture
def auth_client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "test_auth.db"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_DATABASE_PATH", str(db_path))
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret-key")
    monkeypatch.setenv("AUTH_ALLOW_REGISTRATION", "true")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_DOCKER_CONTROL_ENABLED", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    reset_user_store()
    reset_history_repository()
    reset_training_repository()
    reset_sheets_job_repository()
    reset_audio_storage()
    reset_ai_power_state()
    reset_synthesize_jobs()
    reset_rate_limit_state()

    from decime_api.config import settings as live_settings

    live_settings.auth_enabled = True
    live_settings.auth_database_path = str(db_path)
    live_settings.auth_jwt_secret = "test-secret-key"
    live_settings.auth_allow_registration = True
    live_settings.database_url = None
    live_settings.llm_provider = "fake"
    live_settings.tts_provider = "fake"
    live_settings.stt_provider = "fake"
    live_settings.ai_docker_control_enabled = False
    live_settings.audio_storage_dir = str(tmp_path / "audio")
    live_settings.n8n_automation_key = None
    live_settings.n8n_export_webhook_url = None
    live_settings.n8n_import_webhook_url = None
    live_settings.google_dictionary_spreadsheet_id = None
    save_ai_power_state(AiPowerState())

    from decime_api.dependencies import (
        get_llm_provider,
        get_stt_provider,
        get_training_extractor,
        get_tts_provider,
    )

    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()
    app.dependency_overrides[get_stt_provider] = lambda: FakeSTTProvider()
    app.dependency_overrides[get_tts_provider] = lambda: FakeTTSProvider()
    app.dependency_overrides[get_training_extractor] = lambda: FakeTrainingExtractor()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    reset_user_store()
    reset_sheets_job_repository()
    reset_training_repository()
    reset_ai_power_state()
    app.dependency_overrides.clear()
