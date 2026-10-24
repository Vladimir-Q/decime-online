# Report 1 — Human pairwise (Experiment 1)

**Status:** Complete (2026-10-17)  
**Artifacts:** `apps/api/evals/reports/pilot-2026-10/report1_human/`

## Decision locks

- **One criterion:** Style Preservation (`style preservation` in LangSmith PAQ)
- Annotator: project owner (no IAA)
- Experiments annotated: first Stage 3 upload (`…-2214-…`), not the later cost-metadata re-upload

## Result (role mapping)

| Role | Model | Wins |
|------|-------|------|
| A | `gpt-5.6-luna` | **9** |
| B | `gpt-6-luna` | **18** |
| Equal | — | **3** |

**Primary winner (style):** **B / `gpt-6-luna`** (18/30 = 60%). Equal rate 3/30 = 10%.

Export (LangSmith): `python apps/api/scripts/eval_report1_human.py`  
Rebuild from saved cases (no LLM):  
`python apps/api/scripts/eval_report1_human.py --from-json evals/reports/pilot-2026-10/report1_human/report1_human.json`
