# LLM Eval Pilot — Stage 4 (Human pairwise / Exp 1)

**Date:** 2026-10-17  
**Status:** **Done** — integrity OK; owner completed full PAQ on **one** criterion (`style preservation`)  
**Spec:** [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md) §4 / Stage 4  
**Depends on:** Stage 3 human A/B ([stage3](llm_eval_stage3.md))

---

## 1. Goal

Prepare Experiment 1 human pairwise comparison (`esuy_ru_human_v1`) so every PAQ item joins the **same `case_id`** from models A and B — not “row order luck”.

| Item | Value |
|------|--------|
| Dataset | `decime-pilot-esuy_ru_human_v1` |
| Experiment A | from Stage 3 manifest (`gpt-5.6-luna`) |
| Experiment B | from Stage 3 manifest (`gpt-6-luna`) |
| Tool | LangSmith **Pairwise Annotation Queue** |
| Labels | `A better` / `B better` / `Equal` |
| Criteria | **Style Preservation only** (owner lock; other rubric items unused) |

---

## 2. Why integrity matters

LangSmith PAQs pair runs from two experiments **chronologically**. Decime keys pairs by `case_id`. The integrity script checks:

1. **Local Stage 3 reports** — same 30 ids, non-empty RU outputs, no case errors.
2. **LangSmith chronology** — start-time sequences of `case_id` for A and B are identical (so PAQ pairing matches case_id).

CLI:

```bash
cd apps/api
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate

python scripts/eval_stage4_pair_check.py

# Offline (no LangSmith API):
python scripts/eval_stage4_pair_check.py --local-only
```

Artifacts: `apps/api/evals/reports/pilot-2026-10/stage4/pair_integrity.{json,md}`

---

## 3. Create Pairwise Annotation Queue (owner)

1. Open LangSmith → project **`decime-eval-pilot`** → Datasets & Experiments.
2. Open dataset **`decime-pilot-esuy_ru_human_v1`**.
3. Select **exactly two** experiments (A and B from the Stage 3 manifest).
4. Click **Annotate** → **Add to Pairwise Annotation Queue**.
5. Create a new queue, e.g. `decime-pilot-human-pairwise-v1`.
6. Add rubric items (feedback keys):

| Key | Description |
|-----|-------------|
| `semantic_fidelity` | Primary — meaning / facts / constraints (RU) |
| `russian_naturalness` | Natural Russian |
| `nuance_preservation` | Hedges, emotion, soft irony |
| `style_preservation` | Register / politeness / WhatsApp vs Live tone |

7. Instructions for annotator: compare RU translations of the same Spanish source; ignore model names if visible; use Equal when neither is clearly better.

**Blinding:** Experiment metadata still contains model ids (`gpt-5.6-luna` / `gpt-6-luna`). Prefer comparing from the PAQ UI (outputs only). Document residual UI leakage if model names appear in the sidebar.

Compare link pattern (org-scoped): open the dataset → select both experiments → Compare.

---

## 4. Practice gate — complete

Owner confirmed practice labels in the Pairwise Annotation Queue (Stage 4 OK).

---

## 5. Next

- **Stage 6:** full Exp 1 annotation (remaining pairs, all 4 criteria) + Report 1  
- Report 2 (judge): Stage 5 full scores already on disk  
- Stage 7: simulations
