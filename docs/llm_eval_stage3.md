# LLM Eval Pilot — Stage 3 report (A/B → LangSmith)

**Date:** 2026-10-17  
**Status:** **Done for Experiment 1 + Experiment 2 A/B** — judge scoring is Stage 5  
**Spec:** [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md)

---

## 1. What Stage 3 delivered

### Experiment 1 — human suite

| Item | Value |
|------|--------|
| Suite | `esuy_ru_human_v1` (30 cases, owner-approved) |
| Model A | `gpt-5.6-luna` (`EVAL_MODEL_A`) |
| Model B | `gpt-6-luna` (`EVAL_MODEL_B`) |
| Operation | `understand_incoming` (es-UY → RU) |
| Errors | **0** / 30 for A and B |
| Deterministic pass | ~90% each (keyword guards; not quality truth) |
| LangSmith project | `decime-eval-pilot` |
| Dataset | `decime-pilot-esuy_ru_human_v1` |
| Experiment A | `pilot-esuy_ru_human_v1-A-20261017-2214-4443a5e1` |
| Experiment B | `pilot-esuy_ru_human_v1-B-20261017-2214-08a1218c` |

### Experiment 2 — judge suite (candidates only)

| Item | Value |
|------|--------|
| Suite | `ru_esuy_judge_v1` (30 cases, owner-approved) |
| Operation | `translate_to_esuy` (RU → es-UY) |
| Errors | **0** / 30 for A and B |
| Deterministic pass | **100%** each |
| Dataset | `decime-pilot-ru_esuy_judge_v1` |
| Experiment A | `pilot-ru_esuy_judge_v1-A-20261017-2313-1f945468` |
| Experiment B | `pilot-ru_esuy_judge_v1-B-20261017-2313-0bed45d0` |

Local artifacts: `apps/api/evals/reports/pilot-2026-10/stage3/`

CLI: `apps/api/scripts/eval_stage3_ab.py`  
Judge scoring: [llm_eval_stage5.md](llm_eval_stage5.md)

---

## 2. How it works

1. Run Decime eval runner twice with model override (same prompts / no temperature).
2. Upsert LangSmith dataset examples (`case_id` + understand input).
3. Create two experiments whose targets replay local outputs keyed by `case_id` (so LangSmith sessions align for pairwise).
4. Each replay attaches a child `run_type=llm` span with Decime-captured `usage_metadata` (tokens + estimated USD via `input_cost` / `output_cost` / `total_cost`, plus `ls_model_name`) so LangSmith cost columns are populated even though the experiment does not re-call OpenAI.

Product VM tracing stays off (`LLM_TRACING_ENABLED=false`). Only the eval script talks to LangSmith via `LANGSMITH_API_KEY`.

**Note:** Experiments uploaded before this cost wiring show ~$0 — re-run Stage 3 OpenAI upload to refresh costs.

---

## 3. Owner check (manual)

1. Open LangSmith project **`decime-eval-pilot`**.
2. Open dataset **`decime-pilot-esuy_ru_human_v1`**.
3. Compare experiments A vs B — confirm same 30 `case_id`s, outputs present, model names in metadata.
4. Spot-check 2–3 translations.

UI compare links were printed in the CLI log (organization-scoped).

---

## 4. Re-run commands

```bash
cd apps/api
source .venv/Scripts/activate

# Wiring
python scripts/eval_stage3_ab.py --provider fake --suite esuy_ru_human_v1

# Paid human suite
python scripts/eval_stage3_ab.py --provider openai --suite esuy_ru_human_v1

# Later: judge suite (RU→es)
python scripts/eval_stage3_ab.py --provider openai --suite ru_esuy_judge_v1
```

---

## 5. Next

- Experiment 2 judge: [llm_eval_stage5.md](llm_eval_stage5.md) (full done)
- Experiment 1 human pairwise: [llm_eval_stage4.md](llm_eval_stage4.md)
