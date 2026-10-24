# Report 2 — LLM-as-a-Judge (Experiment 2)

- Suite: `ru_esuy_judge_v1` (RU → es-UY)
- Judge: `gpt-5-mini` (Structured Outputs, 4 criteria 1–5)
- Model A: `gpt-5.6-luna` · Model B: `gpt-6-luna`
- Pairs: **30** (60 judged outputs)
- Judge cost (est. USD): **0.111621**
- Critical errors: A=0 · B=0

## Means by role

- A (`gpt-5.6-luna`): semantic_fidelity=4.8, uy_naturalness=4.433, style_preservation=4.7, no_additions_omissions=4.8
- B (`gpt-6-luna`): semantic_fidelity=4.833, uy_naturalness=4.467, style_preservation=4.933, no_additions_omissions=4.867

## Paired comparison (primary = semantic_fidelity)

- A better: **3**
- B better: **4**
- Equal: **23**
- Primary winner (count): **B**

## Paired wins by criterion

| criterion | A_better | B_better | equal |
|-----------|----------|----------|-------|
| semantic_fidelity | 3 | 4 | 23 |
| uy_naturalness | 5 | 6 | 19 |
| style_preservation | 0 | 7 | 23 |
| no_additions_omissions | 1 | 2 | 27 |

## Per-case primary (SF)

| case_id | SF_A | SF_B | winner | UY_A | UY_B |
|---------|------|------|--------|------|------|
| judge-ru-01 | 5 | 5 | equal | 4 | 4 |
| judge-ru-02 | 3 | 4 | B_better | 3 | 3 |
| judge-ru-03 | 5 | 5 | equal | 4 | 5 |
| judge-ru-04 | 5 | 5 | equal | 5 | 5 |
| judge-ru-05 | 5 | 5 | equal | 5 | 5 |
| judge-ru-06 | 4 | 4 | equal | 3 | 3 |
| judge-ru-07 | 5 | 5 | equal | 5 | 5 |
| judge-ru-08 | 5 | 5 | equal | 4 | 4 |
| judge-ru-09 | 5 | 5 | equal | 4 | 4 |
| judge-ru-10 | 4 | 5 | B_better | 5 | 4 |
| judge-ru-11 | 4 | 5 | B_better | 3 | 4 |
| judge-ru-12 | 5 | 5 | equal | 5 | 5 |
| judge-ru-13 | 5 | 5 | equal | 4 | 5 |
| judge-ru-14 | 5 | 5 | equal | 4 | 4 |
| judge-ru-15 | 5 | 4 | A_better | 5 | 5 |
| judge-ru-16 | 5 | 5 | equal | 5 | 5 |
| judge-ru-17 | 5 | 5 | equal | 4 | 5 |
| judge-ru-18 | 5 | 5 | equal | 5 | 5 |
| judge-ru-19 | 5 | 5 | equal | 5 | 5 |
| judge-ru-20 | 4 | 5 | B_better | 5 | 4 |
| judge-ru-21 | 5 | 5 | equal | 4 | 5 |
| judge-ru-22 | 5 | 5 | equal | 4 | 4 |
| judge-ru-23 | 5 | 4 | A_better | 5 | 4 |
| judge-ru-24 | 5 | 4 | A_better | 5 | 4 |
| judge-ru-25 | 5 | 5 | equal | 5 | 4 |
| judge-ru-26 | 5 | 5 | equal | 5 | 5 |
| judge-ru-27 | 5 | 5 | equal | 5 | 5 |
| judge-ru-28 | 5 | 5 | equal | 5 | 5 |
| judge-ru-29 | 5 | 5 | equal | 4 | 5 |
| judge-ru-30 | 5 | 5 | equal | 4 | 4 |
