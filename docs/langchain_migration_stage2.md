# Stage 2 — OpenAI via LangChain

**Date:** 2026-10-15  
**Status:** Implemented behind `LLM_ORCHESTRATOR=langchain` (default remains **`legacy`**)

---

## What changed

`OpenAILLMProvider` now supports two orchestrators:

| Flag | Path |
|------|------|
| `legacy` (default) | `AsyncOpenAI.chat.completions.create` + hand JSON schema (unchanged) |
| `langchain` | `ChatPromptTemplate \| ChatOpenAI.with_structured_output(..., method=json_schema, strict=True)` via `ainvoke` |

Shared between paths:

- Prompt markdown via `lc.prompt_loader`
- User message builders (`_compose_user_content`, `_understand_user_content`)
- Spanish contamination retry
- Dialect stamp fill
- `log_llm_usage` (LC extracts tokens from `AIMessage.usage_metadata`)

Operations covered: **`translate_to_esuy`**, **`understand_incoming`**.  
Training extract / Ollama: still Stage 3–4.

---

## Install

```bash
cd apps/api
pip install -e ".[dev,langchain]"
```

Observed local pins after install (2026-10-15):

```text
langchain-openai 1.7.2
langchain-core   1.6.11
openai           3.31.0
```

---

## Enable LangChain (local / eval only)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_ORCHESTRATOR=langchain
```

Do **not** set this on production without an explicit approval and smoke tests.

---

## Schema note

LangChain requires a top-level JSON Schema `title`. Adapter uses `schema_with_title(reply_bundle_json_schema(), "reply_bundle")` so we keep Decime’s hand schemas (strict-compatible), not auto-generated Pydantic schemas.

---

## Tests (measured)

```text
Full suite: pytest src/decime_api/tests -q
Expected:  all previous + Stage 2 LC unit tests (mocked, no paid API)
```

Live OpenAI A/B comparison is optional and not part of the default suite.
