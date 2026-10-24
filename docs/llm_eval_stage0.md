# LLM Eval Pilot — Stage 0 report

**Date:** 2026-10-17  
**Status:** Probe OK — awaiting LangSmith key + owner go for Stage 1  
**Spec:** [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md)  
**Probe artifacts:** `apps/api/evals/reports/pilot-2026-10/stage0/`

---

## 1. What Stage 0 is

Confirm the plumbing before writing datasets or spending the bulk of the USD 4 budget:

1. Audit existing Decime eval + LangChain code.
2. Probe locked models A / B / Judge with **one tiny call each**.
3. Set up LangSmith from scratch (owner account).
4. Decide go/no-go for Stage 1 (dataset drafts).

---

## 2. Audit — how things work today

| Piece | Path | Role for the pilot |
|-------|------|--------------------|
| Eval runner | `apps/api/src/decime_api/evals/runner.py` | Runs JSONL suites via `OpenAILLMProvider` (LangChain). **Extend later** for dual-model + LangSmith experiments; do not rewrite FastAPI routes. |
| CLI | `apps/api/scripts/run_llm_eval.py` | Fake/OpenAI suites; optional `--judge` (legacy). |
| Legacy judge | `apps/api/src/decime_api/evals/judge.py` | Single 1–5 score via raw `AsyncOpenAI`. **Replace in Stage 5** with Structured Outputs + 4 criteria. |
| Datasets v1 | `apps/api/evals/datasets/v1/` | Smoke sets only. Pilot uses **new** harder JSONL (Stages 1–2). |
| LangChain chat | `services/ai/lc/openai_backend.py` | `ChatOpenAI` factory — **reuse for probes and later runs**. |
| LangSmith today | `services/ai/lc/tracing.py` | Optional **tracing** only (`LLM_TRACING_ENABLED`). No Datasets / Experiments / Annotation Queues yet. |
| Stage 0 probe | `apps/api/scripts/eval_stage0_probe.py` | **New** — cheap availability check for A/B/Judge. |

**Implication:** Stage 0 does not need a production deploy. All work is local under `apps/api`.

---

## 3. Locked models (budget-safe)

| Role | Model ID | Probe |
|------|----------|--------|
| A | `gpt-5.6-luna` | OK |
| B | `gpt-6-luna` | OK |
| Judge | `gpt-5-mini` | OK |

Ceiling: **USD 4.00**. Probe script writes projection under `evals/reports/pilot-2026-10/stage0/`.

**Finding:** `gpt-6-luna` rejects `temperature=0` (only default `1`). For fair A/B compare, **omit temperature** (API default) for both candidates in later stages — do not set 0 on A only.

---

## 4. Run the probe (local)

```bash
cd apps/api
# Windows: .venv\Scripts\activate
source .venv/bin/activate   # or Windows activate
python scripts/eval_stage0_probe.py
```

Requires `OPENAI_API_KEY` in repo-root `.env` (already used by the API).

**Outputs:**

- `apps/api/evals/reports/pilot-2026-10/stage0/stage0_probe.json`
- `apps/api/evals/reports/pilot-2026-10/stage0/stage0_probe.md`

**Owner check:** open the MD file — all three roles must show `OK` / `ok: true`.

---

## 5. LangSmith greenfield checklist (owner)

Decime has no LangSmith project for this pilot yet. Do this once:

1. Sign up / log in at [https://smith.langchain.com](https://smith.langchain.com).
2. Create an API key (Settings → API Keys).
3. Create a dedicated project, e.g. **`decime-eval-pilot`** (keep separate from production traces).
4. Add to **local** repo-root `.env` (do not commit):

```env
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=decime-eval-pilot
# Keep product tracing off unless you intentionally enable it:
LLM_TRACING_ENABLED=false
```

5. Optional later (Stages 3–4): enable tracing only for eval CLI runs, never required for production VM.

**Owner check:** after key is in `.env`, re-run:

```bash
python scripts/eval_stage0_probe.py
```

and confirm `langsmith_key_present: true` in `stage0_probe.json`.  
(Creating Datasets/Experiments comes in Stages 3–4 — not Stage 0.)

---

## 6. Gates before Stage 1

| Gate | Pass criteria |
|------|----------------|
| Models | Probe: A, B, Judge all `ok: true` |
| Budget | Projection total (+ buffer) **≤ USD 3.50** (or owner accepts documented risk) |
| LangSmith | Account + API key in local `.env` (project created) |
| Spec | Still follow [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md) |

When all gates pass, say **“Stage 1”** — we draft `ru_esuy_judge_v1` (30 harder RU→es-UY cases) for your review **before** any paid translate bulk run.

---

## 7. What we intentionally did not do yet

- No new datasets  
- No 120+60 paid runs  
- No Pairwise Annotation Queue  
- No judge rubric implementation  
- No VM / production changes  
