# Stage 7 — Automated test matrix / CI

**Date:** 2026-10-15  
**Status:** Implemented

---

## Goals

- Default `pytest` and PR CI stay **free** (Fake providers, no live LLM).
- Live OpenAI smoke and paid eval are **opt-in** (env flags + markers + manual workflow).
- Never auto-run LLM-as-a-Judge on every commit.

## Markers

Defined in `apps/api/pyproject.toml`:

| Marker | Purpose |
|--------|---------|
| `unit` | Fast deterministic (reserved) |
| `integration` | FastAPI / Fake providers (reserved) |
| `smoke_llm` | Live OpenAI/Ollama smoke |
| `eval` | Opt-in eval-tier tests |

`conftest.py` **drops** `smoke_llm` and `eval` from collection when no `-m` is given. That way `pytest -m eval` is not defeated by `addopts` AND-ing marker expressions.

Stage 6 Fake eval coverage (`test_evals_stage6.py`) stays **unmarked** so the free suite still asserts deterministic pass rate 100%.

## Modules

| File | Marker | Notes |
|------|--------|-------|
| `test_smoke_llm.py` | `smoke_llm` | Needs `DECIME_LLM_SMOKE=1` + `OPENAI_API_KEY` |
| `test_eval_runner_marked.py` | `eval` | Fake compose sanity + optional paid |
| `test_evals_stage6.py` | (none) | Free Fake full-suite regression |

## Local commands

```bash
cd apps/api

# Free (default)
pytest -q

# Eval marker (Fake; skips paid unless DECIME_RUN_EVAL=1)
pytest -m eval -q

# Live smoke
DECIME_LLM_SMOKE=1 OPENAI_API_KEY=... pytest -m smoke_llm -q

# Paid compose eval
DECIME_RUN_EVAL=1 OPENAI_API_KEY=... pytest -m eval -k openai_compose -q
```

## CI

| Workflow | Trigger | Cost |
|----------|---------|------|
| `api-tests.yml` | push/PR on `apps/api/**` | Free: ruff + default pytest + `pytest -m eval -k "not openai"` |
| `api-llm-smoke.yml` | `workflow_dispatch` only | Paid: needs secret `OPENAI_API_KEY`; optional eval toggle |

Manual smoke inputs: `orchestrator` (`legacy` \| `langchain`), `run_eval` boolean.

## Teaching notes

1. **Marker vs skip**: skip-if-no-key inside a smoke test is good; excluding the module from default collection keeps CI green and quiet.
2. **Do not put `-m not eval` in `addopts`**: CLI `-m eval` would AND with it and collect nothing.
3. **Fake eval in free CI** proves wiring; paid smoke proves provider parity under `LLM_ORCHESTRATOR`.
