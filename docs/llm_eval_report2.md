# Report 2 — LLM-as-a-Judge (Experiment 2)

**Status:** Complete (2026-10-17)  
**Artifacts:** `apps/api/evals/reports/pilot-2026-10/report2_judge/`

## Setup

| Item | Value |
|------|--------|
| Suite | `ru_esuy_judge_v1` (RU → es-UY) |
| Candidates | A=`gpt-5.6-luna`, B=`gpt-6-luna` |
| Judge | `gpt-5-mini` Structured Outputs |
| N | 30 pairs / 60 scored outputs |
| Primary | Semantic Fidelity |
| Judge cost | ≈ USD 0.112 |

## Means

| Criterion | A | B |
|-----------|---|---|
| Semantic Fidelity | 4.800 | **4.833** |
| UY Naturalness | 4.433 | **4.467** |
| Style Preservation | 4.700 | **4.933** |
| No Additions/Omissions | 4.800 | **4.867** |

Critical errors: **0** / **0**.

## Paired wins (primary = SF)

| A better | B better | Equal |
|----------|----------|-------|
| 3 | **4** | 23 |

Primary winner by count: **B** (`gpt-6-luna`) — mostly ties; B edges A on style (7–0–23).

Export: `python apps/api/scripts/eval_report2_judge.py`

## Next

See [Report 3](llm_eval_report3.md) (synthetic) and [Report 4](llm_eval_report4.md) (methodology).
