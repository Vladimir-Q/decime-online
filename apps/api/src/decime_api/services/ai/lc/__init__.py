"""LangChain adapter layer for Decime text LLM (OpenAI-compatible ChatOpenAI).

Business logic stays in reply_composer / training_service / provider post-process.
Fake providers never import langchain packages.
"""

from decime_api.services.ai.lc.orchestrator import require_langchain_for_text, use_langchain
from decime_api.services.ai.lc.tracing import (
    configure_langsmith_tracing,
    tracing_active,
    tracing_allowed,
)

__all__ = [
    "configure_langsmith_tracing",
    "require_langchain_for_text",
    "tracing_active",
    "tracing_allowed",
    "use_langchain",
]
