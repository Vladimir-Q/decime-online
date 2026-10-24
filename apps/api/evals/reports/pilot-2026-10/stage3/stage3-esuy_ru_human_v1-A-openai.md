# Decime LLM eval report - pilot

## Meta (conditions)

- Generated: `2026-10-17T23:03:30.224391+00:00`
- Provider: `openai`
- Orchestrator: `langchain`
- Model: `gpt-5.6-luna`
- Suites: `['esuy_ru_human_v1']`
- Judge enabled: `False`
- Cases: `30`

## Measured results

| Metric | Value |
|--------|-------|
| Deterministic pass rate | 90.00% |
| Deterministic passed | 27 |
| Error rate | 0.00% |
| Latency p50 (ms) | 1864.0 |
| Latency p95 (ms) | 3703.0 |
| Judge mean score | None |

## Interpretation notes

- Deterministic metrics are **measured** against suite `expect` rules.
- Judge scores (if present) are **LLM opinions**, not ground truth.
- Fake provider results validate wiring; they are **not** quality claims for production models.

## Failed / errored cases

- `human-es-16` suite=`esuy_ru_human_v1` failed=['forbid_latin_letters'] error=None
- `human-es-19` suite=`esuy_ru_human_v1` failed=['forbid_latin_letters'] error=None
- `human-es-30` suite=`esuy_ru_human_v1` failed=['forbid_latin_letters'] error=None
