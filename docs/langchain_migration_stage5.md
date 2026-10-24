# Stage 5 — LangSmith tracing

**Date:** 2026-10-15  
**Status:** Implemented; **off by default**

---

## Policy

| Condition | Result |
|-----------|--------|
| Default | Tracing **off** |
| `LLM_TRACING_ENABLED=true` + API key + `APP_ENV!=production` | Tracing **on** |
| `APP_ENV=production` | Still **off** unless `LLM_TRACING_ALLOW_PRODUCTION=true` |
| Missing API key | Forced **off** (warning logged) |
| Shell `LANGSMITH_TRACING=true` without Decime flag | Forced **off** at startup |

Default privacy: `LANGSMITH_HIDE_IO=true` → `LANGSMITH_HIDE_INPUTS/OUTPUTS=true` (no prompt/response bodies in LangSmith until you opt out for synthetic demos).

**Do not** send real user WhatsApp/chat content to LangSmith until a masking/PII policy is approved.

Admin token costs remain in Decime `log_llm_usage` — LangSmith is for debugging runs, not billing.

---

## Local setup (synthetic traces)

1. Create a project at [smith.langchain.com](https://smith.langchain.com/).
2. Copy API key.
3. Install LC stack if needed: `pip install -e ".[dev,langchain]"`.
4. In `.env`:

```env
LLM_ORCHESTRATOR=langchain
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_TRACING_ENABLED=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=decime-local
LANGSMITH_HIDE_IO=false
```

5. Restart API. Check `/health` → `llm_tracing: true`.
6. Call compose/understand with **synthetic** text only.
7. In LangSmith UI: open project → find runs named `decime.translate_to_esuy`, `decime.understand_incoming`, etc.

### How to read a trace

1. Filter by tag `decime` or `operation:translate_to_esuy`.
2. Open a run → inspect latency, child LLM spans, errors.
3. With hide_io off (synthetic only): review inputs/outputs for prompt regressions.
4. Metadata includes `decime_provider`, `decime_model`, `decime_app_env`.

### Turn off

```env
LLM_TRACING_ENABLED=false
```

Or omit the key. Startup always clears tracing env when policy denies.

---

## Code

- `services/ai/lc/tracing.py` — gates, env apply, `build_run_config`, `redact_secrets`
- `structured_chat.py` — passes `config=run_name/tags/metadata` into `ainvoke`
- `main.py` lifespan — `configure_langsmith_tracing()`
- `/health` — `llm_orchestrator`, `llm_tracing`

## Tests

`tests/test_lc_tracing_stage5.py` — default off, prod block, enable local, redact, run config.
