# Decime LLM eval datasets — v1

Synthetic cases only (no real user / WhatsApp content).

| File | Suite | Operation |
|------|-------|-----------|
| `compose_ru_esuy.jsonl` | `compose_ru_esuy` (smoke, 3) | `translate_to_esuy` |
| `compose_ru_esuy_30.jsonl` | `compose_ru_esuy_30` (extended, 30) | `translate_to_esuy` |
| `compose_en_esuy.jsonl` | `compose_en_esuy` | `translate_to_esuy` |
| `understand_esuy_ru.jsonl` | `understand_esuy_ru` | `understand_incoming` |
| `understand_esuy_en.jsonl` | `understand_esuy_en` | `understand_incoming` |
| `extract_lexicon.jsonl` | `extract_lexicon` | `extract_candidates` |

Suites named `compose_*` are **translation-only** (RU/EN → es-UY). No `incoming_text` / reply-composition mode.

Each line is one JSON object: `id`, `suite`, `input`, `expect`.

Filter by **suite field**, not filename. Same suite name in two files merges cases.

Expand toward 100–200 cases by appending lines; keep `dataset_version: v1` in reports.

## Edit in Excel

Human-friendly round-trip (`.xlsx`, not legacy `.xls`):

```bash
cd apps/api
pip install openpyxl   # or: pip install -e ".[dev]"

# Export for editing
python scripts/eval_dataset_xlsx.py export \
  evals/datasets/v1/compose_ru_esuy_30.jsonl \
  evals/datasets/v1/compose_ru_esuy_30.xlsx

# After edits in Excel / LibreOffice / Sheets — import back
python scripts/eval_dataset_xlsx.py import \
  evals/datasets/v1/compose_ru_esuy_30.xlsx \
  evals/datasets/v1/compose_ru_esuy_30.jsonl
```

- Lists (`must_contain_any`, …): cell values separated by ` | `
- Booleans: `true` / `false`
- Empty `incoming_text` → JSON `null`
- Do not rename dotted headers (`input.source_text`, `expect.min_reply_chars`, …)

