# Engineering Case Study: Building and Evaluating Decime UY

**From locale-aware translation to a testable, observable LLM application**

[Русская версия](case-study.ru.md) · [README](../README.md) · [Documentation index](README.md)

This document explains how Decime UY was designed, which trade-offs were accepted, how LLM quality was measured, and what remains limited. Claims below point at code, tests, or evaluation artifacts in this repository.

---

## 1. Problem and requirements

Uruguayan Spanish (especially Montevideo Rioplatense) is not interchangeable with “generic Latin American Spanish” in everyday chat. *Voseo*, informal register, and local phrasing affect whether a reply sounds natural on WhatsApp or in person. Learners also need **semantic fidelity**—keeping meaning while sounding local—and often want a **simpler A2** variant when their Spanish is limited.

A single prompt of the form “translate this into Uruguayan Spanish” is insufficient for a product because:

- Inbound and outbound flows differ (`understand_incoming` vs `translate_to_esuy`).
- The UI must receive **stable JSON** fields (translation, tones, training candidates), not free-form prose.
- Speech (STT/TTS) and personal vocabulary training share the same backend contracts.
- Operators need to know **which prompt revision** produced a given output when comparing models or debugging regressions.

Product scope and UX constraints are summarized in [product_brief.md](product_brief.md) and [project_state.md](project_state.md).

---

## 2. Architecture and design decisions

### FastAPI application boundary

The API (`apps/api`) separates routers, domain services, provider interfaces, and persistence. Text LLM, STT, and TTS sit behind replaceable providers so Fake implementations can run CI without paid calls. See [development_brief.md](development_brief.md) and [api_contracts.md](api_contracts.md).

**Trade-off:** A monorepo with a thin Next.js client keeps the LLM boundary on the server (schemas, retries, usage logging). The cost is that mobile and web must share the same API discipline rather than calling model APIs directly.

### LangChain without agent sprawl

Text generation uses LangChain `ChatOpenAI` under `LLM_ORCHESTRATOR=langchain`—the only allowed orchestrator ([langchain_migration_status.md](langchain_migration_status.md)). The path is a composed chat + structured output call, not a multi-agent planner.

**Trade-off:** Less framework magic, clearer stack traces. Complex tool-calling agents were deferred because the product needs deterministic translate/understand/extract contracts more than autonomous planning.

### Structured Outputs

Responses are constrained with JSON Schema and `strict=True` in [`structured_chat.py`](../apps/api/src/decime_api/services/ai/lc/structured_chat.py) and schemas in [`llm_json_schemas.py`](../apps/api/src/decime_api/services/ai/llm_json_schemas.py). Application code validates and maps fields into Pydantic models.

**Trade-off:** Structured Outputs reduce parse failures and ambiguous field names; they do **not** guarantee translation quality. Quality still needs human and judge evaluation.

### Speech separated from text

STT (Whisper / faster-whisper / edge) and TTS (Orpheus via Ollama voice model, or OpenAI TTS) are independent providers. Ollama is **not** used for translate/understand text. That split keeps GPU/voice hosting optional for a text-only local run ([local_stt_setup.md](local_stt_setup.md), [orpheus_tts_setup.md](orpheus_tts_setup.md)).

### PostgreSQL persistence

Production auth, history, training items, and asynchronous dictionary jobs use Postgres (Compose on the VM). Locally, auth can stay off with in-memory / file fallbacks. Migrations live under `supabase/` / deploy Postgres—see [database_schema.sql](database_schema.sql) and [vm_auth.md](vm_auth.md).

### Deployment

Docker Compose under [`deploy/`](../deploy/) runs API, web, Postgres, Caddy, speech services, and optional Cloudflare tunnel. Security expectations are documented in [security_brief.md](security_brief.md)—HTTPS, JWT, CORS, firewall—not “enterprise high availability” claims.

---

## 3. Prompt engineering and version management

### The reproducibility problem

Translation behavior depends on **both** markdown system prompts and Python-assembled human instructions (channel, user level, A2 wording, Spanish-retry reinforcement). Changing either can change outputs, but early traces did not identify an immutable prompt revision.

### Implemented solution

Decime registers four private LangSmith prompts as `ChatPromptTemplate` (system + human, Mustache variables) and resolves an environment tag to a **commit hash once at process startup**. Details: [langsmith_prompt_management.md](langsmith_prompt_management.md), code in [`prompt_templates.py`](../apps/api/src/decime_api/services/ai/lc/prompt_templates.py), [`prompt_provider.py`](../apps/api/src/decime_api/services/ai/lc/prompt_provider.py), [`prompt_hub.py`](../apps/api/src/decime_api/services/ai/lc/prompt_hub.py).

| Mechanism | Role |
|-----------|------|
| Prompt commit (`commit_hash`) | Immutable revision id |
| Tags `staging`, `v1-0-0` | Environment / semver pointers (hyphenated; LangSmith disallows dots in tags) |
| Local snapshots | JSON copies under [`prompts/snapshots/`](../apps/api/src/decime_api/prompts/snapshots/) — fallback only if hash matches |
| `schema_sha256` | Hash of the Python JSON schema, versioned separately from prompt text |
| Code revision | `git rev-parse HEAD` or `DECIME_CODE_REVISION` for images without git |

The app does **not** pull a prompt on every user request: tag resolution is startup-scoped so mid-flight traffic does not silently switch templates.

### Production activation status (explicit)

Infrastructure for LangSmith Prompt Management is in the repository and private prompts exist with `staging` / `v1-0-0` pointing at baseline commits. **Runtime default remains `DECIME_PROMPT_SOURCE=local`.** The `production` tag was not created. Switching the VM requires an explicit owner decision and restart ([project_state.md](project_state.md)).

---

## 4. LLM evaluation methodology

The October 2026 pilot used two complementary **real** experiments plus separate **simulations**. Spec and stage notes: [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md), reports [1](llm_eval_report1.md)–[4](llm_eval_report4.md).

### Why two methods

| Method | Purpose | Limits |
|--------|---------|--------|
| **Human pairwise** | Subjective style / conversational feel | Expensive; one annotator → no IAA |
| **LLM-as-a-Judge** | Scalable multi-criteria numeric scores | Judge bias; correlated errors with related models |

Originally, a four-criterion human rubric was considered. The **completed** human experiment was locked to a **single criterion: style preservation** ([report1_human.json](../apps/api/evals/reports/pilot-2026-10/report1_human/report1_human.json) `criteria_note`).

### Configuration (real)

**Experiment 1 — Human**

- Suite: `esuy_ru_human_v1`, direction es-UY → RU
- Models: A = `gpt-5.6-luna`, B = `gpt-6-luna`
- N = 30 paired cases; annotator = project owner
- LangSmith experiments under the first Stage 3 upload (`…-2214-…`)

**Experiment 2 — Judge**

- Suite: `ru_esuy_judge_v1`, direction RU → es-UY
- Same candidate models; **judge** = `gpt-5-mini` (separate from candidates)
- N = 30 cases, 60 judged translations
- Criteria (1–5): semantic fidelity, UY naturalness, style preservation, no additions/omissions
- Structured judge output + usage/cost metadata in Stage 5 artifacts

Shared practices: aligned case ids, pair-integrity checks ([`pair_integrity.py`](../apps/api/src/decime_api/evals/pair_integrity.py)), LangSmith Datasets/Experiments for upload and PAQ labeling.

---

## 5. Results and model selection

### Human style preference (real)

| Outcome | Count |
|---------|------:|
| A better (`gpt-5.6-luna`) | 9 |
| B better (`gpt-6-luna`) | 18 |
| Equal | 3 |

Source: case labels in [`report1_human.json`](../apps/api/evals/reports/pilot-2026-10/report1_human/report1_human.json). Aggregates now report Equal = 3 and `equal_rate = 0.1`. An earlier markdown/summary export showed Equal = 0 because title-case `Equal` labels were counted under the key `equal`—a reporting bug fixed by rebuilding from saved cases (no new annotations).

**Interpretation:** In this sample, B was preferred on style more often than A. That is a **sample preference**, not a large-scale proof of superiority.

### Judge means (real)

From [`report2_judge.json`](../apps/api/evals/reports/pilot-2026-10/report2_judge/report2_judge.json):

| Metric | A mean | B mean |
|--------|-------:|-------:|
| Semantic fidelity | 4.800 | 4.833 |
| UY naturalness | 4.433 | 4.467 |
| Style preservation | 4.700 | 4.933 |
| No additions/omissions | 4.800 | 4.867 |

Primary semantic-fidelity pairwise outcomes: **3 A / 4 B / 23 equal**. High tie rates mean small mean differences should not be over-read.

Critical errors recorded: 0 / 0. Estimated judge cost in the report artifact: about **$0.11** for the judged set (see `judge_estimated_cost_usd` in the JSON)—not a full production traffic cost model.

### Production default

Pilot takeaway (Report 4): text default → **`gpt-6-luna`**, driven primarily by the human style preference and a slight judge edge, with explicit acknowledgment that N=30 is underpowered for strong claims. Candidate **end-to-end latency** comparisons across models were not published as a complete table in the pilot artifacts; where latency is absent, this case study does not invent numbers.

---

## 6. Statistical analysis and uncertainty

Report 3 ([llm_eval_report3.md](llm_eval_report3.md), [`report3_synthetic/`](../apps/api/evals/reports/pilot-2026-10/report3_synthetic/)) runs **Monte Carlo / synthetic** paired observations:

- 400 human-like A/B/Equal draws
- 400 judge-like scored pairs

These calibrate sign-test power and type-I behavior under assumed effect sizes. Headline simulation note: sign-test power at N=30 for the small-effect scenario is about **0.05** (underpowered); even N=400 remains below an 80% power target in that scenario.

**Simulations cannot increase the precision of the real N=30 experiments.** They only illustrate how little power a small pairwise pilot has under optimistic assumptions. Bootstrap CIs and sign tests on the real pairs should be read with the same caution—see Report 4 methodology write-up under `apps/api/evals/reports/pilot-2026-10/report4_methodology/`.

---

## 7. Engineering challenges and solutions

### 7.1 LLM language contamination

**Problem.** `translate_to_esuy` sometimes returned text still in the source (UI) language.  
**Root cause.** Model non-compliance with locale instructions under mixed-language context.  
**Solution.** Detect contamination (`reply_language.py`) and retry once with Spanish reinforcement (`openai_llm.py`).  
**Verification.** Unit coverage around reply language behavior (`test_reply_language.py`).  
**Limits.** Heuristic detection; rare edge cases can still slip through.

### 7.2 Asynchronous n8n / Sheets job states

**Problem.** Concurrent callbacks and timeouts could move jobs out of terminal `completed` / `failed` states.  
**Root cause.** Non-atomic status updates racing with webhooks.  
**Solution.** Sticky terminal transitions with `UPDATE … WHERE status = ANY(...)` in [`sheets_jobs.py`](../apps/api/src/decime_api/db/sheets_jobs.py).  
**Verification.** [`test_sheets_job_transitions.py`](../apps/api/src/decime_api/tests/test_sheets_job_transitions.py); Postgres race tests require `DECIME_SHEETS_PG_URL` on a DB name containing `test`.  
**Limits.** Full production E2E of the n8n workflow graph remains operator-owned ([project_state.md](project_state.md)).

### 7.3 Model cost accounting

**Problem.** Silent fallback pricing hid unknown models.  
**Root cause.** Hard-coded assumptions about model ids.  
**Solution.** Versioned catalog in [`llm_pricing.py`](../apps/api/src/decime_api/services/analytics/llm_pricing.py); unknown → `unknown_price`.  
**Verification.** [`test_llm_pricing.py`](../apps/api/src/decime_api/tests/test_llm_pricing.py).  
**Limits.** Catalog must be updated when new model ids appear; historical rows are not silently repriced without migration policy.

### 7.4 Prompt reproducibility and CI pins

**Problem.** Prompt text and CI lint versions drifted (`ruff` unpinned → different findings).  
**Solution.** LangSmith commit hashes + local snapshots for prompts; pin `ruff==0.17.1` for reproducible lint.  
**Verification.** Prompt provider tests (`test_prompt_provider.py`); free CI workflow [`.github/workflows/api-tests.yml`](../.github/workflows/api-tests.yml).  
**Limits.** Comparative quality evals after prompt edits were intentionally **not** re-run in the prompt-management change; old scores stay historical.

---

## 8. Reliability, privacy and operations

Implemented controls include JWT auth and per-user data isolation when `AUTH_ENABLED=true` ([vm_auth.md](vm_auth.md), tests such as `test_user_isolation.py` / `test_http_user_isolation.py`), secrets via env files (not committed), optional LangSmith tracing, prompt snapshot fallback with hash checks, Postgres backups via deploy scripts, and Fake LLM paths for unpaid CI.

This is **not** presented as a security certification, multi-region HA platform, or compliance program. Production is a single-operator VM deployment with documented hardening ([security_brief.md](security_brief.md)).

Tracing and eval uploads can contain prompt/user text—operators must treat LangSmith projects and API keys as sensitive and avoid publishing real user messages in public materials.

---

## 9. Lessons learned and future work

1. **Evaluate the product path you ship.** Human style on understand and multi-criteria judge on translate answer different product questions; mixing them without saying so misleads.
2. **Prompt versioning is prerequisite for honest before/after claims.** Without commit ids, “we improved the prompt” is anecdotal.
3. **Structured Outputs stabilize integration, not quality.** Schema success ≠ good Spanish.
4. **Reliability often fails outside the LLM**—job state machines, CI pins, pricing catalogs.
5. **State uncertainty explicitly.** N=30 with many judge ties and one human annotator supports directional decisions, not marketing claims of superiority.
6. **Prefer inspectable composition over agent frameworks** until the product needs tools/planning.

Realistic next steps (from project tracking): device QA for WhatsApp share, optional promotion of LangSmith `production` after owner review, stronger prompt-regression automation against frozen datasets, conversation sessions / onboarding UX, and larger multi-annotator evals if quality claims need to grow.

---

## Evidence index

| Topic | Primary evidence |
|-------|------------------|
| Architecture / status | [project_state.md](project_state.md), [langchain_migration_status.md](langchain_migration_status.md) |
| Prompts | [langsmith_prompt_management.md](langsmith_prompt_management.md), `services/ai/lc/prompt_*.py` |
| Human results | `apps/api/evals/reports/pilot-2026-10/report1_human/` |
| Judge results | `apps/api/evals/reports/pilot-2026-10/report2_judge/` |
| Simulations | `apps/api/evals/reports/pilot-2026-10/report3_synthetic/` |
| Methodology | [llm_eval_report4.md](llm_eval_report4.md) |
| CI | `.github/workflows/api-tests.yml`, `web-ci.yml` |
| Deploy | `deploy/README.md`, [security_brief.md](security_brief.md) |
