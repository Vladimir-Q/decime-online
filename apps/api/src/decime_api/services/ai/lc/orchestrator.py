"""LangChain is the only supported text orchestration path."""

from __future__ import annotations

from decime_api.config import settings


def use_langchain() -> bool:
    """True when text LLM calls go through the LangChain adapter (always in product)."""
    return settings.llm_orchestrator == "langchain"


def require_langchain_for_text() -> None:
    """Fail fast if a non-LangChain orchestrator is configured (unsupported)."""
    if not use_langchain():
        raise RuntimeError(
            "Only LLM_ORCHESTRATOR=langchain is supported for text. "
            "Use OpenAI or an OpenAI-compatible API via ChatOpenAI "
            "(optional OPENAI_TEXT_BASE_URL)."
        )
