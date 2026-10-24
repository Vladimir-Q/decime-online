# Report 3 — Synthetic statistical analysis

**Status:** Complete (2026-10-17)  
**Artifacts:** `apps/api/evals/reports/pilot-2026-10/report3_synthetic/`

> **SIMULATED.** Do not treat N=400 as enlarging the real N=30 pilot. Not evidence of real superiority.

## Simulations

| Name | Kind | N | Seed / params |
|------|------|---|----------------|
| `synthetic_human_esuy_ru_400` | A/B/Equal (style) | 400 | p=(0.38, 0.47, 0.15), seed=20261017 |
| `synthetic_judge_ru_esuy_400` | 1–5 × 4 criteria | 400 | mean_A=4.7, bias_B=0.12, seed=20261024 |

Effect scenario: **small** (calibrated toward Report 1/2, shrunk toward null).

## Headline (simulated)

| | Result |
|--|--------|
| Human-like counts | A=135, B=215, eq=50 |
| Judge primary SF pairs | A=53, B=73, eq=274 |
| Sign-test power @ N=30 | ~0.05 (underpowered) |
| Sign-test power @ N=400 | ~0.46 (still &lt; 80% target) |
| Null @ N=400 | ~0.05 (type-I OK) |

## Commands

```bash
cd apps/api
python scripts/eval_report3_synthetic.py
# optional charts:
# jupyter notebook evals/reports/pilot-2026-10/report3_synthetic/report3_synthetic.ipynb
```

## Next

See [Report 4](llm_eval_report4.md) — methodology summary (complete).
