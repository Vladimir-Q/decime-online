"""Stage 5: LangSmith tracing gates (no network calls to LangSmith)."""

from __future__ import annotations

import os

import pytest

from decime_api.services.ai.lc.tracing import (
    build_run_config,
    configure_langsmith_tracing,
    redact_secrets,
    tracing_active,
    tracing_allowed,
)

_MANAGED_ENV = (
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGCHAIN_PROJECT",
    "LANGSMITH_HIDE_INPUTS",
    "LANGSMITH_HIDE_OUTPUTS",
)


@pytest.fixture(autouse=True)
def _reset_tracing_env():
    saved = {key: os.environ.get(key) for key in _MANAGED_ENV}
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    # Restore Decime default: tracing forced off.
    configure_langsmith_tracing()


def test_tracing_off_by_default() -> None:
    assert tracing_allowed() is False
    assert tracing_active() is False


def test_configure_forces_tracing_env_off_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.llm_tracing_enabled",
        False,
    )
    configure_langsmith_tracing()
    assert os.environ.get("LANGSMITH_TRACING") == "false"
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"
    assert tracing_active() is False


def test_production_blocks_without_allow_flag(monkeypatch) -> None:
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.llm_tracing_enabled",
        True,
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.app_env",
        "production",
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.llm_tracing_allow_production",
        False,
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.langsmith_api_key",
        "lsv2_test_key",
    )
    assert tracing_allowed() is False
    configure_langsmith_tracing()
    assert os.environ.get("LANGSMITH_TRACING") == "false"


def test_tracing_enables_with_key_in_local(monkeypatch) -> None:
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.llm_tracing_enabled",
        True,
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.app_env",
        "local",
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.llm_tracing_allow_production",
        False,
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.langsmith_api_key",
        "lsv2_test_key",
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.langsmith_project",
        "decime-test",
    )
    monkeypatch.setattr(
        "decime_api.services.ai.lc.tracing.settings.langsmith_hide_io",
        True,
    )
    snapshot = configure_langsmith_tracing()
    assert tracing_allowed() is True
    assert tracing_active() is True
    assert os.environ.get("LANGSMITH_TRACING") == "true"
    assert os.environ.get("LANGSMITH_PROJECT") == "decime-test"
    assert os.environ.get("LANGSMITH_HIDE_INPUTS") == "true"
    assert snapshot["LANGSMITH_API_KEY"] == "***"


def test_redact_secrets() -> None:
    text = "Authorization: Bearer abc.def.ghi and key sk-abcdefghijklmnopqrstuvwxyz"
    redacted = redact_secrets(text)
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "Bearer abc.def.ghi" not in redacted
    assert "[REDACTED]" in redacted


def test_build_run_config_names() -> None:
    cfg = build_run_config(
        operation="translate_to_esuy",
        provider="openai",
        model="gpt-4o-mini",
    )
    assert cfg is not None
    assert cfg["run_name"] == "decime.translate_to_esuy"
    assert "provider:openai" in cfg["tags"]
    assert cfg["metadata"]["decime_operation"] == "translate_to_esuy"
