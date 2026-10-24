"""Map LangChain usage metadata into Decime llm_usage logging."""

from __future__ import annotations

from typing import Any


def tokens_from_ai_message(message: Any) -> tuple[int, int, int]:
    """Return (prompt_tokens, completion_tokens, total_tokens) from an AIMessage."""
    usage = getattr(message, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        prompt = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        completion = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        return prompt, completion, total

    prompt = int(getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or (prompt + completion))
    return prompt, completion, total


def tokens_from_structured_raw(raw_result: Any) -> tuple[int, int, int]:
    """Extract tokens from ``include_raw=True`` structured-output result dict."""
    if isinstance(raw_result, dict):
        message = raw_result.get("raw")
        if message is not None:
            return tokens_from_ai_message(message)
    return 0, 0, 0
