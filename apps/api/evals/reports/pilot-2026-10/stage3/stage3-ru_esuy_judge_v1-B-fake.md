# Decime LLM eval report - pilot

## Meta (conditions)

- Generated: `2026-10-17T23:09:46.409280+00:00`
- Provider: `fake`
- Orchestrator: `langchain`
- Model: `fake-compose-v1`
- Suites: `['ru_esuy_judge_v1']`
- Judge enabled: `False`
- Cases: `30`

## Measured results

| Metric | Value |
|--------|-------|
| Deterministic pass rate | 6.67% |
| Deterministic passed | 2 |
| Error rate | 0.00% |
| Latency p50 (ms) | 0.0 |
| Latency p95 (ms) | 0.0 |
| Judge mean score | None |

## Interpretation notes

- Deterministic metrics are **measured** against suite `expect` rules.
- Judge scores (if present) are **LLM opinions**, not ground truth.
- Fake provider results validate wiring; they are **not** quality claims for production models.

## Failed / errored cases

- `judge-ru-01` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-02` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-03` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-04` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-05` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-06` suite=`ru_esuy_judge_v1` failed=['min_reply_chars'] error=None
- `judge-ru-07` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-08` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-10` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-11` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-12` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-13` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-14` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-15` suite=`ru_esuy_judge_v1` failed=['must_contain_any'] error=None
- `judge-ru-16` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-17` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-18` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-19` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-20` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-21` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-23` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-24` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-25` suite=`ru_esuy_judge_v1` failed=['must_contain_any'] error=None
- `judge-ru-26` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-27` suite=`ru_esuy_judge_v1` failed=['must_contain_any'] error=None
- `judge-ru-28` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-29` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
- `judge-ru-30` suite=`ru_esuy_judge_v1` failed=['min_reply_chars', 'must_contain_any'] error=None
