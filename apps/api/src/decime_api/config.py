from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/decime_api/config.py → repo root is 4 levels up
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ROOT_ENV = _REPO_ROOT / ".env"
_API_ENV = Path(__file__).resolve().parents[2] / ".env"

_INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me-in-production",
        "change-me",
        "secret",
        "test-secret-key",
    }
)

# Capacitor / WebView — required for Android APK (not a public browser origin).
_CAPACITOR_ORIGINS = frozenset(
    {
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
        "ionic://localhost",
        "null",
    }
)


def _env_files() -> tuple[str, ...]:
    paths: list[Path] = []
    if _ROOT_ENV.exists():
        paths.append(_ROOT_ENV)
    if _API_ENV.exists() and _API_ENV not in paths:
        paths.append(_API_ENV)
    return tuple(str(path) for path in paths)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    app_name: str = "Decime UY"
    app_locale_default: str = "es-UY-montevideo"
    frontend_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    # Text LLM: fake (tests) | openai (OpenAI or OpenAI-compatible API). No local text models.
    llm_provider: Literal["fake", "openai"] = "fake"
    # Text orchestration: LangChain only (value kept for health/evals metadata).
    llm_orchestrator: Literal["langchain"] = "langchain"
    # LangSmith (Stage 5). Off by default. Production also needs llm_tracing_allow_production.
    llm_tracing_enabled: bool = False
    llm_tracing_allow_production: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "decime-local"
    # Prefer hide I/O until a masking policy for real user text is approved.
    langsmith_hide_io: bool = True
    # Prompt versions. local = checked-in templates. langsmith = hub commit pinned at startup.
    decime_prompt_source: Literal["local", "langsmith"] = "local"
    decime_prompt_env: str = "production"
    decime_prompt_snapshot_dir: str | None = None
    decime_prompt_pins: str | None = None
    decime_code_revision: str | None = None
    stt_provider: Literal["fake", "openai", "ollama", "faster_whisper", "local"] = "fake"
    tts_provider: Literal["fake", "openai", "orpheus"] = "fake"
    speech_provider: Literal["fake", "openai"] | None = None

    # Ollama hosts Orpheus TTS voice model (and optional Ollama STT) — not text LLM.
    ollama_base_url: str = "http://localhost:11434"
    ollama_stt_model: str = "karanchopda333/whisper:latest"

    orpheus_tts_base_url: str = "http://localhost:5005"
    orpheus_tts_model: str = "orpheus"
    orpheus_tts_voice: str = "javi"
    orpheus_ollama_model: str = "sematre/orpheus:it_es"
    whisper_model_size: str = "base"
    whisper_cpu_threads: int = 0  # 0 = library default; eco profile sets 1–2
    whisper_num_workers: int = 1

    # Admin Start/Stop for local Orpheus TTS containers (Docker socket).
    ai_docker_control_enabled: bool = False
    ai_docker_socket: str = "/var/run/docker.sock"
    ai_docker_project: str = "decime"

    openai_api_key: str | None = None
    openai_text_model: str = "gpt-6-luna"
    # OpenAI-compatible chat API (DeepSeek, Groq, etc.). Empty = official OpenAI.
    openai_text_base_url: str | None = None
    openai_stt_model: str = "gpt-4o-mini-transcribe"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "coral"
    # OpenAI-compatible Whisper on edge PC (Tailscale), e.g. http://100.x.x.x:8090/v1
    openai_stt_base_url: str | None = None

    audio_storage_dir: str = "data/audio"
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    auth_enabled: bool = False
    auth_database_path: str = "data/decime.db"
    auth_jwt_secret: str = "change-me-in-production"
    auth_jwt_expire_minutes: int = 60 * 24 * 7
    auth_allow_registration: bool = False
    auth_bootstrap_admin_email: str | None = None
    auth_bootstrap_admin_password: str | None = None

    # Dictionary ↔ n8n / Google Sheets (server-side only; never expose to the browser).
    n8n_export_webhook_url: str | None = None
    n8n_import_webhook_url: str | None = None
    n8n_automation_key: str | None = None
    google_dictionary_spreadsheet_id: str | None = None
    dictionary_sheets_job_timeout_minutes: int = 30
    dictionary_sheets_max_import_rows: int = 5000
    n8n_webhook_timeout_seconds: float = 10.0

    def cors_allowed_origins(self) -> list[str]:
        """Production: only web origins per docs/security_brief.md + Capacitor."""
        if self.app_env == "local":
            return ["*"]

        origins: set[str] = set(_CAPACITOR_ORIGINS)
        base = self.frontend_base_url.rstrip("/")
        if base:
            origins.add(base)
            if base.startswith("https://") and "://www." not in base:
                origins.add(base.replace("https://", "https://www.", 1))
        return sorted(origins)

    @property
    def auth_database_file(self) -> Path:
        path = Path(self.auth_database_path)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        return path

    @property
    def audio_storage_path(self) -> Path:
        path = Path(self.audio_storage_dir)
        if not path.is_absolute():
            path = _REPO_ROOT / path
        return path

    @property
    def use_postgres(self) -> bool:
        return bool(self.database_url)

    def validate_postgres_auth(self) -> None:
        if self.use_postgres and not self.auth_enabled:
            raise ValueError(
                "DATABASE_URL requires AUTH_ENABLED=true for per-user data isolation"
            )

    def validate_production_security(self) -> None:
        """docs/security_brief.md — fail fast on unsafe public deploy."""
        if self.app_env != "production":
            return

        if not self.auth_enabled:
            raise ValueError("APP_ENV=production requires AUTH_ENABLED=true")

        if len(self.auth_jwt_secret) < 32:
            raise ValueError("AUTH_JWT_SECRET must be at least 32 characters in production")

        if self.auth_jwt_secret in _INSECURE_JWT_SECRETS:
            raise ValueError("AUTH_JWT_SECRET must not use a default placeholder in production")

        if not self.frontend_base_url.startswith("https://"):
            raise ValueError("FRONTEND_BASE_URL must use https:// in production")

        if not self.api_base_url.startswith("https://"):
            raise ValueError("API_BASE_URL must use https:// in production")

        if self.auth_allow_registration:
            raise ValueError(
                "AUTH_ALLOW_REGISTRATION must be false for public MVP "
                "(create users via admin only)"
            )

    @property
    def openapi_enabled(self) -> bool:
        """Interactive OpenAPI docs are for local/dev only."""
        return self.app_env != "production"


settings = Settings()
