"""Shared types for the LangChain adapter (Stage 1 contracts)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

LcOperation = Literal[
    "translate_to_esuy",
    "understand_incoming",
    "extract_candidates",
    "normalize_dictionary_row",
    "llm_judge_translate",
]


class StructuredInvokeResult(TypedDict, total=False):
    """Normalized adapter result before Decime Pydantic validation / post-process."""

    data: dict[str, Any]
    provider: str
    model: str
    operation: LcOperation
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
