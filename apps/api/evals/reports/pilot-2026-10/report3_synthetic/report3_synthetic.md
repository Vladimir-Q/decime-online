# Report 3 — Synthetic statistical analysis

> **SIMULATED.** Not real model evidence. N=400 does not enlarge the real N=30 pilot.

- Effect scenario: **small**
- Generated: 2026-10-17T23:51:13.318672+00:00

## Simulation A — human-like (`synthetic_human_esuy_ru_400`)

- Params: p_A=0.38, p_B=0.47, p_eq=0.15, seed=20261017
- Criterion: `style_preservation`
- Counts: {'A_better': 135, 'B_better': 215, 'equal': 50}
- Win rate A: 0.3375 CI95 [0.29, 0.385]
- Win rate B: 0.5375 CI95 [0.4875, 0.5875]
- Sign test p (ties dropped): 2.2e-05

## Simulation B — judge-like (`synthetic_judge_ru_esuy_400`)

- Params: mean_A=4.7, bias_B=0.12, noise_sd=0.45, seed=20261024
- Primary: `semantic_fidelity`
- Pair counts: {'A_better': 53, 'equal': 274, 'B_better': 73}
- Mean SF A/B: 4.532 / 4.593
- Mean paired diff B−A: 0.06 CI95 [0.0, 0.12]
- Sign test p: 0.090123

## Power sensitivity (sign test, α=0.05)

- Small-effect power at **N=30** (real pilot size): **0.0525**
- Small-effect power at **N=400** (synthetic only): **0.463**
- Null-effect power at N=400 (false positive rate check): **0.049**

Target power 80% is not reached at N=30 under this small-effect multinomial — consistent with treating the real pilot as exploratory.
