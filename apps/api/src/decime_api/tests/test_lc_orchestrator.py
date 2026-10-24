"""LangChain feature flag and prompt loader."""

import pytest
from pydantic import ValidationError

from decime_api.config import Settings, settings
from decime_api.services.ai.lc import use_langchain
from decime_api.services.ai.lc.orchestrator import require_langchain_for_text
from decime_api.services.ai.lc.prompt_loader import (
    load_prompt,
    translate_to_esuy_system_prompt,
)


def test_llm_orchestrator_defaults_to_langchain() -> None:
    assert settings.llm_orchestrator == "langchain"
    assert use_langchain() is True
    require_langchain_for_text()  # does not raise


def test_legacy_orchestrator_rejected_by_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_ORCHESTRATOR", "legacy")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_prompt_loader_reads_translate_to_esuy() -> None:
    text = translate_to_esuy_system_prompt()
    assert "Uruguayan" in text or "uruguay" in text.lower() or "es-UY" in text
    assert load_prompt("translate_to_esuy.md") == text
