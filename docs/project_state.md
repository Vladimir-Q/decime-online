# Decime UY — Project State (single-context snapshot)

**Last updated:** 2026-10-24 (Publication-readiness branch: docs/security hygiene; prompts still local)   


**Read this first.** Agent guide: [../AGENTS.md](../AGENTS.md). Doc index: [README.md](README.md). **Active Cursor tasks:** [decime_uy_cursor_product_task.md](decime_uy_cursor_product_task.md), [decime_uy_cursor_technical_task.md](decime_uy_cursor_technical_task.md). Reports: [reports/](reports/).

---

## Phase status

| Phase | Status |
|-------|--------|
| 0 Skeleton | ✅ |
| 1 Text composer | ✅ |
| 2 Audio STT/TTS | ✅ |
| 3 Add to training | ✅ |
| 4 Review + SRS | ✅ |
| 5 WhatsApp / Quick Reply | ✅ web + APK · **🚧 device QA** |
| 6 Auth + VM deploy | ✅ — JWT, Postgres, `decime.online` |
| 7 Persistence (Postgres) | ✅ — training + history + SRS + event_log |
| **8 Pre-beta polish** | **🚧** — Live Chat, UI English, prod fixes |

---

## Production (VM)

| URL | Role |
|-----|------|
| `https://decime.online` | Static web (nginx) |
| `https://api.decime.online` | FastAPI (Caddy TLS) |

**Stack on VM:** Docker Compose — postgres, api, web, caddy, ollama, orpheus, cloudflare tunnel profile.

**Providers in prod:** `LLM_PROVIDER=openai` (`gpt-6-luna`), `STT_PROVIDER=faster_whisper`, `TTS_PROVIDER=orpheus`.

**Deploy:**

```bash
cd ~/decime/deploy
# Requires external Docker network decime_n8n (n8n shared VM).
./dc.sh --profile tunnel up -d --build
# Includes: shared-vm + tunnel + speech overlay + docker-compose.n8n-net.yml
```

See [deploy/README.md](../deploy/README.md), [vm_auth.md](vm_auth.md), [security_brief.md](security_brief.md).

**E2E smoke test:** `scripts/vm_internal_e2e.py` (14 checks — auth, compose, incoming, training, audio).

---

## What works now

### Quick Reply (`/app/quick-reply`) — WhatsApp-first
- ES → UI lang (`understand`) then UI lang → es-UY (`translate/text`) — **translation only**, no LLM reply composition
- Tone chips: Recommended / Simple A2; one `recommended_reply`
- Play audio, Copy/Share WhatsApp, Add to training

### Live Chat (`/app/live`) — in-person
- Mic-first + text fallback; auto-detect ES ↔ RU/EN direction
- **Web:** microphone device selector (Refresh to grant permission)
- One translation output; Add to training for Spanish replies

### Navigation
- **Web:** Dashboard · Quick Reply · Live Chat · History · Training · Diagnostics · Settings
- **Mobile APK:** Quick Reply · Live Chat · Training · History · Settings (parity with web)
- **Settings:** UI language + logout only (no API URL field)
- **Diagnostics (dev/LAN APK):** API URL scan / manual entry
- `/app/compose` and `/app/audio` redirect to Live Chat (legacy URLs)

### Training (`/app/training`)
- Extract candidates (~30s) → approve → save with optional TTS
- Locale normalization (`es-UY` → `es-UY-montevideo`)
- Review + SRS at `/app/training/review`

### Auth
- `AUTH_ENABLED=true` on production; JWT on all protected routes
- Postgres `app_users`; per-user training lists and history
- Login `/login/`; admin `/app/admin/users/`

### Android shell (Capacitor)
- **Production APK:** `.\scripts\build-android-apk.ps1` → API `https://api.decime.online`, login required
- **Dev APK:** `.\scripts\build-android-apk.ps1 -Dev` → LAN / emulator
- Nav: Quick Reply · Live Chat · Training · History · Settings (parity with web)
- WhatsApp share in/out; Live Chat mic + text
- Setup: [android_setup.md](android_setup.md)

### API (protected when auth enabled)
| Endpoint | Purpose |
|----------|---------|
| `GET /health` | status, providers, models |
| `GET/POST /api/v1/auth/*` | config, login, register, users |
| `POST /api/v1/incoming/understand-text` | ES → RU/EN translation |
| `POST /api/v1/translate/text` | RU/EN → es-UY translation |
| `POST /api/v1/training/extract-candidates` | LLM extract items |
| `POST /api/v1/training/approve-candidates` | Save approved items |
| `GET /api/v1/training/lists` · `items` · `review/*` | Training + SRS |
| `POST /api/v1/audio/transcribe` · `synthesize` | STT / TTS |
| `GET /api/v1/audio/files/{id}` | Playback (JWT required) |
| `GET/DELETE /api/v1/history` | Compose history |

**Tests:** ~100 free pytest (`apps/api`; excludes `smoke_llm` + `eval` markers). Web: `npm run typecheck` + `npm run build` (CI: `web-ci.yml`).

### LangChain / LLM (current)

- Text: **OpenAI / OpenAI-compatible only** via LangChain (`LLM_ORCHESTRATOR=langchain` — only allowed value). No local Ollama text; no legacy orchestrator.
- Optional `OPENAI_TEXT_BASE_URL` for DeepSeek/Groq/etc.
- Adapter: `apps/api/src/decime_api/services/ai/lc/` (`ChatOpenAI`)
- Ollama remains for **Orpheus TTS** only
- Fake LLM: pytest/CI only
- Evals (unfinished harness): `python scripts/run_llm_eval.py --provider fake|openai`
- Status: [langchain_migration_status.md](langchain_migration_status.md)

---

## Run locally (Git Bash)

```bash
# scripts/start_local.sh — Ollama + Orpheus + API + Web
cd apps/api && source .venv/Scripts/activate
uvicorn decime_api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

cd apps/web && npm run dev
```

---

## Next (pre-beta)

- [ ] Device QA: WhatsApp share on physical phone ([android_setup.md](android_setup.md))
- [ ] Product task: unified Assistant UX, onboarding, hide diagnostics in prod mobile
- [ ] Conversation sessions + Start new conversation
- [ ] LocaleCriticUY, split compose models (see cursor technical task)
- [x] Dictionary Sheets Decime-n8n API chain audited (set VM `N8N_*` / spreadsheet id; E2E workflow still operator-owned)
- [x] **LLM eval pilot** — Reports 1–4 complete ([r1](llm_eval_report1.md)–[r4](llm_eval_report4.md)); prod text = `gpt-6-luna`. Report 1 human Equal count corrected to **3/30** (rebuild from saved labels; no LLM).
- [x] Ruff pinned to 0.17.1; sheets jobs cannot leave `completed`/`failed`; LLM cost uses a versioned catalog (`unknown_price` instead of a silent mini fallback).
- [x] LangSmith prompt commits for the four live operations. `staging` and `v1-0-0` point at the baseline. `DECIME_PROMPT_SOURCE` remains `local`. `production` tag is not set. See [langsmith_prompt_management.md](langsmith_prompt_management.md).
- [ ] **Public Git readiness** — this clean-history copy is prepared for publish; license + owner push still required. See [publication-readiness.md](publication-readiness.md).

## Out of scope

Twilio and Palabra — [out_of_scope.md](out_of_scope.md).
