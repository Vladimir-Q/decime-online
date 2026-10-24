# Decime UY — agent & developer guide

This file is for **Cursor agents and contributors**.  
End users and VM operators: see [README.md](README.md). Deploy detail: [deploy/README.md](deploy/README.md).

## Stack

- **Frontend:** Next.js (PWA, mobile-first) — `apps/web`
- **Backend:** FastAPI — `apps/api`
- **Database:** Supabase Postgres + Storage — `supabase/` (VM uses Compose Postgres)
- **AI:** OpenAI or Ollama (LLM) + local Whisper STT + Orpheus or OpenAI TTS — see [docs/README.md](docs/README.md)

## Documentation

**Full index:** [docs/README.md](docs/README.md).

| Doc | Purpose |
|-----|---------|
| [docs/case-study.md](docs/case-study.md) | Engineering case study (EN) · [RU](docs/case-study.ru.md) |
| [README.ru.md](README.ru.md) | Russian product/engineering overview |
| [docs/project_state.md](docs/project_state.md) | **Current state** — read first in a new session |
| [docs/reports/product_status_report.md](docs/reports/product_status_report.md) | Product status (screens, flows) |
| [docs/reports/technical_status_report.md](docs/reports/technical_status_report.md) | Technical status (API, storage, stack) |
| [docs/development_brief.md](docs/development_brief.md) | Architecture and implementation |
| [docs/product_brief.md](docs/product_brief.md) | Product scope and UX |
| [docs/api_contracts.md](docs/api_contracts.md) | REST API shapes |
| [docs/prompt_contracts.md](docs/prompt_contracts.md) | LLM prompt rules |
| [docs/langsmith_prompt_management.md](docs/langsmith_prompt_management.md) | LangSmith prompt commits, staging, rollback |
| [docs/prod_llm_translate_payload.md](docs/prod_llm_translate_payload.md) | Prod translate LLM payload (system/human/schema) |
| [docs/database_schema.sql](docs/database_schema.sql) | Postgres schema draft |
| [docs/local_stt_setup.md](docs/local_stt_setup.md) | Local Whisper STT (Windows) |
| [docs/orpheus_tts_setup.md](docs/orpheus_tts_setup.md) | Local Orpheus TTS |
| [docs/edge_speech_tailscale.md](docs/edge_speech_tailscale.md) | Edge STT/TTS over Tailscale |
| [docs/android_setup.md](docs/android_setup.md) | Capacitor Android + WhatsApp share |
| [docs/vm_auth.md](docs/vm_auth.md) | JWT auth for VM deployment |
| [docs/mvp_tasks.md](docs/mvp_tasks.md) | Phase checklist |
| [docs/qa_checklist.md](docs/qa_checklist.md) | Manual QA |
| [docs/out_of_scope.md](docs/out_of_scope.md) | Twilio, Palabra — not planned |
| [docs/cursor_working_rules.md](docs/cursor_working_rules.md) | Cursor agent rules (summary below) |

## Local setup

### 1. Environment

```bash
cp .env.example .env
```

**Recommended local stack** (`.env` — matches `.env.example`):

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_ORCHESTRATOR=langchain
# OPENAI_TEXT_BASE_URL=   # optional OpenAI-compatible endpoint
STT_PROVIDER=faster_whisper
WHISPER_MODEL_SIZE=base
TTS_PROVIDER=orpheus
ORPHEUS_TTS_BASE_URL=http://localhost:5005
OLLAMA_BASE_URL=http://localhost:11434
ORPHEUS_OLLAMA_MODEL=sematre/orpheus:it_es
AUTH_ENABLED=false
```

Text is OpenAI / OpenAI-compatible via LangChain only. Ollama is for Orpheus TTS (voice model), not for translate/understand. For cloud TTS use `TTS_PROVIDER=openai`.

Setup guides: [docs/local_stt_setup.md](docs/local_stt_setup.md), [docs/orpheus_tts_setup.md](docs/orpheus_tts_setup.md), [scripts/start_local.sh](scripts/start_local.sh).

### 2. Backend (FastAPI)

```bash
cd apps/api
py -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev,local-stt]"
uvicorn decime_api.main:app --reload --app-dir src
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected (fields vary with `.env`):

```json
{
  "status": "ok",
  "app": "Decime UY",
  "env": "local",
  "auth_enabled": "false",
  "llm_provider": "openai",
  "llm_orchestrator": "langchain",
  "stt_provider": "faster_whisper",
  "tts_provider": "orpheus"
}
```

### 3. Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3b. Android (Capacitor, optional)

See [docs/android_setup.md](docs/android_setup.md). Build a debug APK:

```powershell
.\scripts\build-android-apk.ps1
```

APK path: `apps/web/android/app/build/outputs/apk/debug/app-debug.apk`

On the phone, open **Settings** in the app to scan the LAN or enter your PC API URL. Run the API with `--host 0.0.0.0`.

### 4. Tests

```bash
cd apps/api
pytest                 # free suite (Fake LLM; excludes smoke_llm + eval markers)
pytest -m eval         # opt-in eval marker (Fake sanity; paid needs DECIME_RUN_EVAL=1)
pytest -m smoke_llm    # live OpenAI smoke (needs DECIME_LLM_SMOKE=1 + OPENAI_API_KEY)
ruff check src

cd ../web
npm run lint
npm run typecheck
npm run build
```

CI: `.github/workflows/api-tests.yml` (free API), `.github/workflows/web-ci.yml` (typecheck + build). Paid smoke: `.github/workflows/api-llm-smoke.yml` (manual `workflow_dispatch`).
LangChain text path (current): `docs/langchain_migration_status.md`; historical Stages 0–8 in `docs/langchain_migration_stage*.md`.

## Repository layout

```text
decime/
  apps/
    api/          FastAPI backend
    web/          Next.js frontend
  docs/           Product and technical briefs
  deploy/         Docker Compose for production VM
  supabase/       Migrations and seeds
  scripts/        Dev helpers (+ scripts/edge for Tailscale speech)
```

## Phase status

- **Phases 0–7** — MVP core, auth, Postgres persistence ✅
- **Phase 8** — pre-beta polish (Live Chat, UI, prod fixes) 🚧
- **Production:** `https://decime.online` · `https://api.decime.online`

See [docs/mvp_tasks.md](docs/mvp_tasks.md) and [docs/project_state.md](docs/project_state.md).

## Cursor working rules

Read `docs/product_brief.md` and `docs/development_brief.md` before coding.

- Build only MVP features unless explicitly asked.
- Prefer small, testable changes.
- Use typed schemas and structured LLM outputs.
- Keep providers replaceable (STT, TTS, LLM behind interfaces).
- Do not hardcode OpenAI directly into business logic.
- Do not auto-add training items without user approval.
- For learning items, `surface_text` is the primary memorized form; `lemma` is metadata.
- Keep Uruguay/Montevideo as the only active target locale in MVP.
- Avoid full expression extraction in MVP.
- After each coding step, provide validation commands and expected results.

### Session continuity

Before the context window ends, or after any meaningful decision or implementation:

1. Update **`docs/project_state.md`** — current phase, what exists, next task, open items.
2. Update **`docs/mvp_tasks.md`** if tasks were completed or reprioritized.
3. Optionally append to local-only **`docs/conversation_log.md`** (gitignored; not published).

In a new session, read **`docs/project_state.md`** first, then briefs/contracts as needed.

Full copy: [docs/cursor_working_rules.md](docs/cursor_working_rules.md).
