# Decime UY — Documentation index

**Last updated:** 2026-10-24  
**Repository:** `decime/` monorepo (`apps/api`, `apps/web`, `supabase/`, `scripts/`, `deploy/`)

Use this page to find docs for **day-to-day operation**, **architecture**, and **onboarding**.

---

## Start here

| File | Audience | Purpose |
|------|----------|---------|
| [../README.md](../README.md) | Everyone | Product + engineering overview (English) |
| [../README.ru.md](../README.ru.md) | Everyone | Same overview in Russian |
| [case-study.md](case-study.md) | Engineers | **Engineering case study** — architecture, prompts, evals (EN) |
| [case-study.ru.md](case-study.ru.md) | Engineers | Same case study in Russian |
| [../AGENTS.md](../AGENTS.md) | Developers, Cursor agents | Local setup, tests, docs index, working rules |
| [project_state.md](project_state.md) | Developers, Cursor agents | **Current snapshot** — phases, endpoints, run commands |
| [publication-readiness.md](publication-readiness.md) | Maintainers | Safe-to-share summary: inventory, history risks, checklist |
| [../SECURITY.md](../SECURITY.md) | Everyone | Vulnerability reporting and secrets hygiene |
| [reports/product_status_report.md](reports/product_status_report.md) | Product owner | Screens, flows, MVP acceptance (RU) |
| [reports/technical_status_report.md](reports/technical_status_report.md) | Developers, DevOps | Architecture diagram, API list, storage, debt (RU) |

---

## Architecture and contracts

| File | Purpose |
|------|---------|
| [development_brief.md](development_brief.md) | Stack, principles, repo layout, schemas, workflows |
| [product_brief.md](product_brief.md) | Product vision, UX, MVP scope |
| [api_contracts.md](api_contracts.md) | REST shapes (`/api/v1/*`, auth, health) |
| [prompt_contracts.md](prompt_contracts.md) | LLM prompt rules and output schemas |
| [langsmith_prompt_management.md](langsmith_prompt_management.md) | Prompt commits, staging/production tags, snapshots, rollback |
| [prod_llm_translate_payload.md](prod_llm_translate_payload.md) | Prod `translate_to_esuy`: HTTP vs system/human/schema examples |
| [database_schema.sql](database_schema.sql) | Postgres draft (Supabase migrations mirror this) |
| [out_of_scope.md](out_of_scope.md) | Twilio, Palabra — explicitly not planned |
| [langchain_migration_status.md](langchain_migration_status.md) | **Current** LangChain text path (trust this over stage*.md details) |
| [langchain_migration_stage8.md](langchain_migration_stage8.md) | LangChain migration wrap-up / runbooks (read status banner — some diagrams are historical) |
| [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md) | **Agreed** LLM eval pilot (human + judge + simulations); implementation staged |
| [llm_eval_stage0.md](llm_eval_stage0.md) | Stage 0: audit, model probe, LangSmith checklist |
| [llm_eval_stage2.md](llm_eval_stage2.md) | Human dataset `esuy_ru_human_v1` — approved |
| [llm_eval_stage1.md](llm_eval_stage1.md) | Judge dataset `ru_esuy_judge_v1` — approved |
| [llm_eval_stage3.md](llm_eval_stage3.md) | Stage 3: A/B → LangSmith (human + judge suites) |
| [llm_eval_stage4.md](llm_eval_stage4.md) | Stage 4: human pairwise integrity + PAQ |
| [llm_eval_stage5.md](llm_eval_stage5.md) | Stage 5: LLM-as-a-Judge (full 60 done) |
| [llm_eval_report1.md](llm_eval_report1.md) | Report 1: human pairwise (style) — B 18 / A 9 / Equal 3 |
| [llm_eval_report2.md](llm_eval_report2.md) | Report 2: LLM judge — B slight edge, many SF ties |
| [llm_eval_report3.md](llm_eval_report3.md) | Report 3: synthetic 400+400 (simulated only) |
| [llm_eval_report4.md](llm_eval_report4.md) | Report 4: methodology summary (pilot complete) |

**Prompt files (runtime, not docs):** `apps/api/src/decime_api/prompts/` — `translate_to_esuy.md`, `understand_incoming.md`, `extract_training_items.md`, `locale_validate_uy.md`.

---

## Operations — run locally

| File | When to read |
|------|----------------|
| [../.env.example](../.env.example) | All env vars (providers, auth, Orpheus, Supabase) |
| [../scripts/start_local.sh](../scripts/start_local.sh) | Git Bash: Ollama + Orpheus + API + Web tabs |
| [local_stt_setup.md](local_stt_setup.md) | Windows: `faster-whisper` STT |
| [orpheus_tts_setup.md](orpheus_tts_setup.md) | Local Spanish TTS (Orpheus-FastAPI :5005) |
| [../apps/api/README.md](../apps/api/README.md) | API-only setup, pytest, ruff |

**Typical local stack** (see `.env.example`):

```text
LLM_PROVIDER=openai          # text: OpenAI / OpenAI-compatible (LangChain)
LLM_ORCHESTRATOR=langchain
STT_PROVIDER=faster_whisper  # or edge whisper
TTS_PROVIDER=orpheus         # Ollama hosts Orpheus voice only
AUTH_ENABLED=false           # open API for dev
```

**Health check:** `GET http://localhost:8000/health` — returns providers, models, `auth_enabled`.

---

## Operations — Android (Capacitor)

| File | Purpose |
|------|---------|
| [android_setup.md](android_setup.md) | **Production APK** (`api.decime.online`) + dev LAN build |
| [decime_uy_mobile_product_brief.md](decime_uy_mobile_product_brief.md) | Mobile product scope |
| [decime_uy_mobile_technical_brief.md](decime_uy_mobile_technical_brief.md) | Capacitor, native HTTP plugin |

**Scripts:** `scripts/build-android-apk.ps1` (production), `scripts/build-android-apk.ps1 -Dev` (LAN/emulator).

---

## Next phase (pre-beta)

| File | Purpose |
|------|---------|
| [decime_uy_cursor_product_task.md](decime_uy_cursor_product_task.md) | Assistant UX, onboarding, sessions |
| [decime_uy_cursor_technical_task.md](decime_uy_cursor_technical_task.md) | Technical follow-ups |
| [../deploy/README.md](../deploy/README.md) | Docker Compose VM deploy (live) |
| [../scripts/vm_internal_e2e.py](../scripts/vm_internal_e2e.py) | Production E2E smoke test |

---

## Operations — VM / production

| File | Purpose |
|------|---------|
| [security_brief.md](security_brief.md) | **Public deploy security** — HTTPS, firewall, CORS, auth |
| [../deploy/README.md](../deploy/README.md) | Docker Compose: `decime.online` + `api.decime.online` |
| [vm_auth.md](vm_auth.md) | JWT, Postgres users, per-user isolation |
| [../scripts/create_admin.py](../scripts/create_admin.py) | Create admin user manually |
| [../scripts/allow-decime-firewall.ps1](../scripts/allow-decime-firewall.ps1) | Windows firewall for LAN API |

**Manual step:** production is live at `decime.online`. Run Android QA on phone — see [android_setup.md](android_setup.md).

---

## QA and progress tracking

| File | Purpose |
|------|---------|
| [qa_checklist.md](qa_checklist.md) | Manual QA (replies, extraction, E2E MVP) |
| [mvp_tasks.md](mvp_tasks.md) | Phase checklist (through Phase 8 pre-beta) |

---

## Cursor / planned work

| File | Purpose |
|------|---------|
| [decime_uy_cursor_product_task.md](decime_uy_cursor_product_task.md) | Product backlog for agents |
| [decime_uy_cursor_technical_task.md](decime_uy_cursor_technical_task.md) | Technical backlog (VM, Postgres, refactor) |
| [decime_uy_qwen4b_uruguay_locale_technical_doc.md](decime_uy_qwen4b_uruguay_locale_technical_doc.md) | Qwen3 4B + Uruguay locale pack |
| [cursor_working_rules.md](cursor_working_rules.md) | Agent coding rules |

---

## Internal / historical (not for daily ops)

Local-only (gitignored, absent from the current tree): `docs/conversation_log.md` (optional agent session notes), `docs/handoff_edge_speech_*.md` (private edge-network handoff).

**Note:** `.gitignore` does not remove objects from Git history. See [publication-readiness.md](publication-readiness.md) before making the repository public.

---

## Quick architecture (2026-06-23)

```text
Next.js 15 (web + static Capacitor)  ──HTTP/JSON──►  FastAPI :8000
       │                                              │
       └── Android: DecimeApiPlugin (Java)            ├── LLM / STT / TTS providers
                                                       ├── Postgres (if DATABASE_URL)
                                                       ├── Memory (local dev only)
                                                       └── Disk: data/audio/{user_id}/
```

**Protected routes** (when `AUTH_ENABLED=true`): compose, incoming, history, audio, training.  
**Public:** `/health`, `/api/v1/auth/login`, `/api/v1/auth/config`, register (if allowed).
