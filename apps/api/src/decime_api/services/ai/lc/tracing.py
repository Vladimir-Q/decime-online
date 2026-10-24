"""LangSmith tracing gates for Decime (Stage 5).

LangChain auto-traces when ``LANGSMITH_TRACING`` / ``LANGCHAIN_TRACING_V2`` is true.
Decime never enables that by accident: ``LLM_TRACING_ENABLED`` must be set, and
production requires an explicit allow flag. Without credentials, configure is a no-op
and tracing stays off.

Usage metadata for admin cost dashboards remains ``log_llm_usage`` — do not treat
LangSmith token panels as a second billing source.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from decime_api.config import settings
from decime_api.services.ai.lc.types import LcOperation

logger = logging.getLogger(__name__)

_SECRET_RE = re.compile(
    r"(?i)\b(sk-[a-zA-Z0-9_-]{8,}|Bearer\s+[A-Za-z0-9\-._~+/]+=*|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
)


def tracing_allowed() -> bool:
    """Whether Decime policy permits sending traces to LangSmith."""
    if not settings.llm_tracing_enabled:
        return False
    return settings.app_env != "production" or settings.llm_tracing_allow_production


def tracing_active() -> bool:
    """True when policy allows tracing and an API key is available."""
    if not tracing_allowed():
        return False
    key = (settings.langsmith_api_key or os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY") or "").strip()
    return bool(key)


def configure_langsmith_tracing() -> dict[str, str]:
    """Apply or clear process env for LangSmith based on Decime settings.

    Safe to call at app startup and in tests. Returns the effective env snapshot
    for the keys we manage (values may be redacted).
    """
    managed = (
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_PROJECT",
        "LANGCHAIN_PROJECT",
        "LANGSMITH_HIDE_INPUTS",
        "LANGSMITH_HIDE_OUTPUTS",
    )

    if not tracing_allowed():
        # Force off even if the shell exported LANGSMITH_TRACING=true.
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info(
            "LangSmith tracing disabled (llm_tracing_enabled=%s app_env=%s allow_prod=%s)",
            settings.llm_tracing_enabled,
            settings.app_env,
            settings.llm_tracing_allow_production,
        )
        return {k: os.environ.get(k, "") for k in managed}

    api_key = (
        settings.langsmith_api_key
        or os.environ.get("LANGSMITH_API_KEY")
        or os.environ.get("LANGCHAIN_API_KEY")
        or ""
    ).strip()
    if not api_key:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.warning(
            "LLM_TRACING_ENABLED is true but LANGSMITH_API_KEY is missing — tracing stays off"
        )
        return {k: os.environ.get(k, "") for k in managed}

    project = settings.langsmith_project or f"decime-{settings.app_env}"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_PROJECT"] = project

    if settings.langsmith_hide_io:
        os.environ["LANGSMITH_HIDE_INPUTS"] = "true"
        os.environ["LANGSMITH_HIDE_OUTPUTS"] = "true"
    else:
        os.environ.pop("LANGSMITH_HIDE_INPUTS", None)
        os.environ.pop("LANGSMITH_HIDE_OUTPUTS", None)

    logger.info(
        "LangSmith tracing enabled project=%s hide_io=%s",
        project,
        settings.langsmith_hide_io,
    )
    snapshot = {k: os.environ.get(k, "") for k in managed}
    if snapshot.get("LANGSMITH_API_KEY"):
        snapshot["LANGSMITH_API_KEY"] = "***"
    if snapshot.get("LANGCHAIN_API_KEY"):
        snapshot["LANGCHAIN_API_KEY"] = "***"
    return snapshot


def redact_secrets(text: str) -> str:
    """Best-effort scrub of API keys / JWTs from free text (for metadata/logs)."""
    return _SECRET_RE.sub("[REDACTED]", text or "")


def build_run_config(
    *,
    operation: LcOperation,
    provider: str,
    model: str,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """RunnableConfig for ``ainvoke`` — None when tracing is inactive (optional pass-through).

    Always safe to pass to ainvoke; LangChain ignores tracing when env is off.
    We still attach run_name/tags/metadata so local debugging is consistent when enabled.
    """
    metadata: dict[str, Any] = {
        "decime_operation": operation,
        "decime_provider": provider,
        "decime_model": model,
        "decime_app_env": settings.app_env,
        "decime_orchestrator": settings.llm_orchestrator,
    }
    if extra_metadata:
        for key, value in extra_metadata.items():
            if value is None:
                continue
            if isinstance(value, str):
                metadata[key] = redact_secrets(value)[:200]
            else:
                metadata[key] = value

    return {
        "run_name": f"decime.{operation}",
        "tags": [
            "decime",
            f"provider:{provider}",
            f"operation:{operation}",
            f"env:{settings.app_env}",
        ],
        "metadata": metadata,
    }
