"""OpenAI / OpenAI-compatible ChatOpenAI factory for LangChain orchestration."""

from __future__ import annotations

from typing import Any


def build_chat_openai(
    *,
    api_key: str,
    model: str,
    temperature: float | None = None,
    base_url: str | None = None,
) -> Any:
    """Construct async-capable ChatOpenAI. Lazy-imports langchain_openai.

    ``base_url`` selects an OpenAI-compatible endpoint (DeepSeek, Groq, Azure proxy, etc.).
    """
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "model": model,
        "timeout": 120.0,
        "max_retries": 2,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if base_url:
        kwargs["base_url"] = base_url.rstrip("/")
    return ChatOpenAI(**kwargs)


def schema_with_title(schema: dict[str, Any], title: str) -> dict[str, Any]:
    """LangChain requires a top-level ``title`` when passing a raw JSON Schema dict."""
    out = dict(schema)
    out["title"] = title
    return out
