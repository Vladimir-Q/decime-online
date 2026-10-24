# Decime LLM eval report - pilot

## Meta (conditions)

- Generated: `2026-10-17T22:05:21.710059+00:00`
- Provider: `fake`
- Orchestrator: `langchain`
- Model: `fake-compose-v1`
- Suites: `['esuy_ru_human_v1']`
- Judge enabled: `False`
- Cases: `30`

## Measured results

| Metric | Value |
|--------|-------|
| Deterministic pass rate | 3.33% |
| Deterministic passed | 1 |
| Error rate | 0.00% |
| Latency p50 (ms) | 0.0 |
| Latency p95 (ms) | 0.0 |
| Judge mean score | None |

## Interpretation notes

- Deterministic metrics are **measured** against suite `expect` rules.
- Judge scores (if present) are **LLM opinions**, not ground truth.
- Fake provider results validate wiring; they are **not** quality claims for production models.

## Failed / errored cases

- `human-es-01` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
- `human-es-02` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
- `human-es-03` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-04` suite=`esuy_ru_human_v1` failed=['min_chars'] error=None
- `human-es-05` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-06` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-07` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-08` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-09` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
- `human-es-10` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-11` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-12` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-13` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-14` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
- `human-es-15` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-16` suite=`esuy_ru_human_v1` failed=['min_chars'] error=None
- `human-es-17` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
- `human-es-18` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-19` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-20` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-21` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-23` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-24` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-25` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-26` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-27` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-28` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
- `human-es-29` suite=`esuy_ru_human_v1` failed=['must_contain_any'] error=None
- `human-es-30` suite=`esuy_ru_human_v1` failed=['min_chars', 'must_contain_any'] error=None
