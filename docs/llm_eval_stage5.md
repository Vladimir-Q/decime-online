# LLM Eval Pilot — Stage 5 (LLM-as-a-Judge dry-run)

**Date:** 2026-10-17  
**Status:** **Full complete** — 60/60 judge calls OK (`gpt-5-mini`)  
**Spec:** [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md) §5 / Stage 5  
**Depends on:** Stage 3 A/B for `ru_esuy_judge_v1` ([stage3](llm_eval_stage3.md))

---

## 1. What this stage is

Experiment 2 judge path:

1. Candidates already produced by Stage 3 (A=`gpt-5.6-luna`, B=`gpt-6-luna`).
2. Judge model **`gpt-5-mini`** scores each Spanish reply with Structured Outputs.
3. Default CLI is a **2-case dry-run** (4 judge calls). Full 60 requires `--full` after this dry-run artifact exists and owner approval.

---

## 2. Rubric (English, locked)

| Field | Scale | Meaning |
|-------|-------|---------|
| `semantic_fidelity` | 1–5 | **Primary** — facts/constraints/hedges preserved |
| `uy_naturalness` | 1–5 | Natural es-UY / Montevideo Spanish |
| `style_preservation` | 1–5 | Register, politeness, emotion |
| `no_additions_omissions` | 1–5 | No invention / no dropped constraints |
| `critical_error` | bool | Wrong language, empty, inverted meaning, unsafe |
| `rationale` | string | Short English explanation |
| `error_category` | enum | `none` \| `meaning_drift` \| `omission` \| `addition` \| `register_mismatch` \| `unnatural_spanish` \| `wrong_locale` \| `wrong_language` \| `other` |

Judge prompt: `apps/api/src/decime_api/evals/judge_pilot.py`  
Schema: `judge_translate_pilot_json_schema()` in `llm_json_schemas.py`

Judge input includes source RU, candidate Spanish, and request context — **never** candidate model names.

---

## 3. Commands

```bash
cd apps/api
source .venv/Scripts/activate   # or Windows: .venv\Scripts\activate

# Prerequisite (already done for this pilot):
# python scripts/eval_stage3_ab.py --provider openai --suite ru_esuy_judge_v1

# Dry-run (default N=2 → 4 judge calls)
python scripts/eval_stage5_judge.py

# After owner approval:
python scripts/eval_stage5_judge.py --full
```

Env: `OPENAI_API_KEY`, optional `EVAL_JUDGE_MODEL=gpt-5-mini`, `LANGSMITH_API_KEY` for feedback attach.

Artifacts: `apps/api/evals/reports/pilot-2026-10/stage5/`

---

## 4. Dry-run result (2026-10-17)

| Case | Role | SF | UY | ST | NA | critical | category |
|------|------|----|----|----|----|----------|----------|
| judge-ru-01 | A | 5 | 4 | 4 | 5 | false | none |
| judge-ru-01 | B | 5 | 4 | 5 | 5 | false | none |
| judge-ru-02 | A | 4 | 3 | 4 | 4 | false | unnatural_spanish |
| judge-ru-02 | B | 4 | 3 | 4 | 4 | false | unnatural_spanish |

Mean SF ≈ 4.5; judge cost est. ≈ USD 0.011. LangSmith feedback attached (16 scores on Stage 3 experiment runs).

Artifacts: `apps/api/evals/reports/pilot-2026-10/stage5/stage5-ru_esuy_judge_v1-dry-run.md`

## 5. Full run result (2026-10-17)

Owner approved dry-run → `--full`.

| Metric | Value |
|--------|-------|
| Judged | **60** / 60 (0 API errors) |
| Mean SF (primary) | **4.817** (A 4.800 · B 4.833) |
| Mean UY | **4.450** (A 4.433 · B 4.467) |
| Critical errors | **0** |
| Judge cost (est.) | **≈ USD 0.112** |
| LangSmith feedback | 240 score attachments |

Artifacts: `apps/api/evals/reports/pilot-2026-10/stage5/stage5-ru_esuy_judge_v1-full.{json,md}`

## 6. Next

Report 2 aggregation (Exp 2). Human pairwise Stage 4 remains for Exp 1.
