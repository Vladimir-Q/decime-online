# Decime LLM eval report - pilot

## Meta (conditions)

- Generated: `2026-10-17T23:11:22.199809+00:00`
- Provider: `openai`
- Orchestrator: `langchain`
- Model: `gpt-5.6-luna`
- Suites: `['ru_esuy_judge_v1']`
- Judge enabled: `False`
- Cases: `30`

## Measured results

| Metric | Value |
|--------|-------|
| Deterministic pass rate | 100.00% |
| Deterministic passed | 30 |
| Error rate | 0.00% |
| Latency p50 (ms) | 3000.0 |
| Latency p95 (ms) | 4349.0 |
| Judge mean score | None |

## Interpretation notes

- Deterministic metrics are **measured** against suite `expect` rules.
- Judge scores (if present) are **LLM opinions**, not ground truth.
- Fake provider results validate wiring; they are **not** quality claims for production models.

## Failed / errored cases

_None._
