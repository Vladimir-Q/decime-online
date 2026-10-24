# Decime UY API

FastAPI backend for Decime UY.

**Docs:** [docs/README.md](../../docs/README.md) · [api_contracts.md](../../docs/api_contracts.md) · [project_state.md](../../docs/project_state.md) · [LangChain notes](../../docs/langchain_migration_status.md)

## Setup

```bash
cd apps/api
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev,local-stt]"
```

Copy repo root `.env.example` → `.env` at repo root.

Text LLM is **LangChain + OpenAI / OpenAI-compatible only** (`LLM_PROVIDER=openai`, `LLM_ORCHESTRATOR=langchain`). There is no local Ollama text path and no legacy orchestrator rollback.

## Run

```bash
# Local only
uvicorn decime_api.main:app --reload --app-dir src

# Phone / LAN testing
uvicorn decime_api.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Test

```bash
pytest                 # free suite (Fake LLM; excludes smoke_llm + eval)
pytest -m eval         # opt-in eval marker
pytest -m smoke_llm    # live OpenAI (DECIME_LLM_SMOKE=1 + OPENAI_API_KEY)
ruff check src
```

Eval CLI (optional harness): `python scripts/run_llm_eval.py --provider fake`

## Auth (optional)

Set `AUTH_ENABLED=true` in `.env`. See [docs/vm_auth.md](../../docs/vm_auth.md).

Protected routers: compose, incoming, history, audio, training.
