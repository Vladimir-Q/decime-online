# Pilot datasets (LLM eval 2026-10)

Agreed pilot: [docs/llm_eval_pilot_spec.md](../../../../../docs/llm_eval_pilot_spec.md).

**Implementation order (owner decision 2026-10-17):** start with **human** (Experiment 1), then judge (Experiment 2).

| File | Suite | Direction | N | Status |
|------|-------|-----------|---|--------|
| `esuy_ru_human_v1.jsonl` | `esuy_ru_human_v1` | es-UY → RU (`understand_incoming`) | 30 | **Approved** — [stage2](../../../../../docs/llm_eval_stage2.md) |
| `ru_esuy_judge_v1.jsonl` | `ru_esuy_judge_v1` | RU → es-UY (`translate_to_esuy`) | 30 | **Approved** — [stage1](../../../../../docs/llm_eval_stage1.md) |

```bash
cd apps/api
source .venv/Scripts/activate
python scripts/run_llm_eval.py --provider fake --dataset-version pilot --suites esuy_ru_human_v1
```

Do **not** run `--provider openai` until the owner approves the texts.

## Context policy (prod-only)

**Human / understand** (`esuy_ru_*`):

| Field | Rule |
|-------|------|
| `channel` | `whatsapp_text` (QR) or `in_person` (Live) only |
| `source_language` | `es` |
| `target_language` | `ru` (this pilot) |
| `locale_variant` | `es-UY-montevideo` |

**Judge / translate** (`ru_esuy_*`): see [prod_llm_translate_payload.md](../../../../../docs/prod_llm_translate_payload.md) — QR `user_level` omit\|`A2`, Live `in_person` only.

`tags` / `tests` are review-only — not sent to models.

Completed run artifacts (do not regenerate the paid files): [reports/pilot-2026-10](../../reports/pilot-2026-10/README.md). Write-ups: [report 1](../../../../../docs/llm_eval_report1.md)–[report 4](../../../../../docs/llm_eval_report4.md).
