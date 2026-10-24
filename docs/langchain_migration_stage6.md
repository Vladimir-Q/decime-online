# Stage 6 — LLM Evaluation

**Date:** 2026-10-15  
**Status:** Implemented (free Fake path + optional paid provider/judge)

---

## Layout

```text
apps/api/evals/datasets/v1/     # versioned JSONL suites
apps/api/evals/reports/         # generated reports (local)
apps/api/src/decime_api/evals/  # loader, deterministic metrics, judge, runner
apps/api/scripts/run_llm_eval.py
```

## Suites (v1)

| Suite | Cases | Operation |
|-------|------:|-----------|
| compose_ru_esuy | 3 | translate_to_esuy |
| compose_en_esuy | 2 | translate_to_esuy |
| understand_esuy_ru | 2 | understand_incoming |
| understand_esuy_en | 2 | understand_incoming |
| extract_lexicon | 1 | extract_candidates |

Synthetic text only. Expand by appending JSONL lines.

## Metrics

**Deterministic (always, free):**

- non-empty output
- min length
- forbid Cyrillic in Spanish replies / Latin in RU translations
- `must_contain_any` lexical anchors
- required fields / candidate type filters

**LLM-as-a-Judge (optional, paid):**

- Enabled only with `--judge` + `OPENAI_API_KEY`
- Rubric 1–5 for meaning / es-UY / extras (`evals/judge.py`)
- Do **not** use judge for schema/language checks

**Engineering (measured every run):**

- latency p50 / p95 / mean
- error rate
- deterministic pass rate

## Run

```bash
cd apps/api

# CI-safe / wiring check
python scripts/run_llm_eval.py --provider fake

# Real OpenAI, legacy vs LangChain (two runs)
LLM_ORCHESTRATOR=legacy python scripts/run_llm_eval.py --provider openai --suites compose_ru_esuy
LLM_ORCHESTRATOR=langchain python scripts/run_llm_eval.py --provider openai --suites compose_ru_esuy

# Optional judge (extra cost)
python scripts/run_llm_eval.py --provider openai --suites compose_ru_esuy --judge
```

Reports: `evals/reports/eval-v1-<provider>-<orchestrator>.{md,json}`

## LangSmith datasets

JSONL can be uploaded as LangSmith examples (input/expect columns). Prefer synthetic projects only. Tracing (Stage 5) is independent of this runner.

## Cost warning

`--provider openai|ollama` and `--judge` call real models. Do **not** add paid evals to default GitHub Actions without a dedicated workflow and budget cap.
