# Stage 3 — Ollama via LangChain

> **Obsolete (2026-10-16):** Local Ollama text LLM was removed. Product text uses LangChain `ChatOpenAI` only (OpenAI / OpenAI-compatible). Ollama remains for Orpheus TTS. Keep this file as historical migration notes.


**Date:** 2026-10-15  
**Status:** Implemented behind `LLM_ORCHESTRATOR=langchain` (default remains **`legacy`**)

---

## Decisions

| Operation | LangChain path | Why |
|-----------|----------------|-----|
| `translate_to_esuy` | `ChatOllama.with_structured_output(method=json_schema)` | Same ReplyBundle contract as OpenAI LC |
| `understand_incoming` | **Plain text** `ChatPromptTemplate \| ChatOllama` | Matches legacy quality path; no forced JSON schema |

Post-process unchanged: `_normalize_reply_payload`, Spanish contamination retry, `_translation_looks_invalid` + dual prompt retry, dialect stamp.

---

## Code

- `lc/ollama_backend.py` — `build_chat_ollama(base_url, model)`
- `lc/structured_chat.py` — `ainvoke_structured` supports `provider=ollama`; new `ainvoke_plain_text`
- `ollama_llm.py` — branches on `use_langchain()`

## Enable locally

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=qwen3:4b
LLM_ORCHESTRATOR=langchain
```

Requires: `pip install -e ".[dev,langchain]"` and a running Ollama with the model pulled.

## Tests

Mocked unit tests in `tests/test_lc_ollama_stage3.py` (no live Ollama required).
