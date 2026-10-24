"""LCEL structured chat invoke for Decime OpenAI-compatible adapters."""

from __future__ import annotations

import time
from typing import Any

from decime_api.services.ai.lc.callbacks import tokens_from_structured_raw
from decime_api.services.ai.lc.openai_backend import build_chat_openai, schema_with_title
from decime_api.services.ai.lc.tracing import build_run_config
from decime_api.services.ai.lc.types import LcOperation, StructuredInvokeResult


async def ainvoke_structured(
    *,
    operation: LcOperation,
    system_prompt: str,
    user_content: str,
    schema: dict[str, Any],
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    schema_title: str | None = None,
    temperature: float | None = None,
    prompt_metadata: dict[str, Any] | None = None,
    **_: Any,
) -> StructuredInvokeResult:
    """Run ``ChatPromptTemplate | chat.with_structured_output`` via ``ainvoke``."""
    from langchain_core.prompts import ChatPromptTemplate

    started = time.perf_counter()
    title = schema_title or schema.get("title") or operation
    schema_for_lc = schema_with_title(schema, str(title))

    if provider != "openai":
        raise NotImplementedError(
            f"LangChain structured invoke for provider={provider!r} is not supported "
            f"(operation={operation!r}). Use LLM_PROVIDER=openai "
            f"(OpenAI or OpenAI-compatible via OPENAI_TEXT_BASE_URL)."
        )
    if not api_key:
        raise ValueError("api_key is required for OpenAI LangChain invoke")

    chat = build_chat_openai(
        api_key=api_key,
        model=model,
        temperature=temperature,
        base_url=base_url,
    )
    structured = chat.with_structured_output(
        schema_for_lc,
        method="json_schema",
        strict=True,
        include_raw=True,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{user_content}"),
        ]
    )
    chain = prompt | structured
    run_config = build_run_config(
        operation=operation,
        provider=provider,
        model=model,
        extra_metadata=prompt_metadata,
    )
    raw_result = await chain.ainvoke(
        {
            "system_prompt": system_prompt,
            "user_content": user_content,
        },
        config=run_config,
    )

    if not isinstance(raw_result, dict):
        raise TypeError(f"Unexpected structured output type: {type(raw_result)!r}")
    if raw_result.get("parsing_error"):
        raise ValueError(f"Structured output parse error: {raw_result['parsing_error']}")

    parsed = raw_result.get("parsed")
    if parsed is None:
        raise ValueError("Structured output returned empty parsed payload")
    if hasattr(parsed, "model_dump"):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        raise ValueError(f"Unsupported parsed type: {type(parsed)!r}")

    prompt_tokens, completion_tokens, total_tokens = tokens_from_structured_raw(raw_result)
    latency_ms = int((time.perf_counter() - started) * 1000)

    return StructuredInvokeResult(
        data=data,
        provider=provider,
        model=model,
        operation=operation,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
