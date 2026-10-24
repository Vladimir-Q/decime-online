# LLM Eval Pilot — Stage 1 report

**Date:** 2026-10-17  
**Status:** **Owner approved** (2026-10-17) — texts + context accepted; no paid RU→es-UY until Stage 3+ / budget + LangSmith gates  


**Spec:** [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md)  
**Prod request shape:** [prod_llm_translate_payload.md](prod_llm_translate_payload.md)

---

## 1. What this stage delivered

New harder RU → es-UY dataset for Experiment 2 (LLM-as-a-Judge):

| Item | Value |
|------|--------|
| Dataset | `ru_esuy_judge_v1` |
| Path | `apps/api/evals/datasets/pilot/ru_esuy_judge_v1.jsonl` |
| Spreadsheet | `apps/api/evals/datasets/pilot/ru_esuy_judge_v1.xlsx` |
| Cases | **30** unique `id`s and unique `source_text`s |
| Context mix | **22** QR any · **5** QR `user_level=A2` · **3** Live (`in_person`) |
| Operation | `translate_to_esuy` (`source_language: ru`) |
| Paid LLM calls | **None** in this stage |

Smoke check: Fake provider run — **0 errors** (suite wiring OK). Low deterministic pass rate is expected: Fake replies are canned and will not match hard `must_contain_any` keywords.

---

## 2. How the dataset is structured

Each JSONL line:

- `id` — stable case id (`judge-ru-01` … `judge-ru-30`)
- `suite` — `ru_esuy_judge_v1`
- `tags` / `tests` — human review hints (**not** sent to models)
- `input` — `TranslateToEsRequest` shape; `context` is **prod-only**:
  - QR: `channel=whatsapp_text`, optional `user_level` omit (Recommended) or `"A2"` (Simple)
  - Live: `channel=in_person` only (no `user_level`)
  - always `target_locale` (default `es-UY-montevideo`)
  - **no** `tone` / `situation` / `output_options`
- `expect` — light deterministic guards (`forbid_cyrillic`, `min_reply_chars`, optional `must_contain_any`)

Harder than smoke `compose_ru_esuy_30`: multi-clause, emotion, hedges, negation scope, soft irony, triple constraints, Montevideo context.

---

## 3. Owner review (manual) — please do this

1. Open **`apps/api/evals/datasets/pilot/ru_esuy_judge_v1.xlsx`** (or the `.jsonl`).
2. For each row, check:
   - natural conversational Russian;
   - `channel` matches intended screen (QR WhatsApp vs Live in-person);
   - `user_level` blank = Recommended (any); `A2` = Simple chip only on QR rows;
   - no duplicate meaning across cases;
   - constraints you care about are explicit (dates, allergies, payment, etc.).
3. Edit freely in Excel, then import back:

```bash
cd apps/api
source .venv/Scripts/activate
python scripts/eval_dataset_xlsx.py import \
  evals/datasets/pilot/ru_esuy_judge_v1.xlsx \
  evals/datasets/pilot/ru_esuy_judge_v1.jsonl
```

4. Reply with one of:
   - **“Judge Stage OK”** → proceed toward paid judge path (after human Exp 1 is underway/approved)
   - **“fix judge”** + notes → we revise texts

**Do not approve paid RU→es-UY judge runs until this review is done.** Prefer finishing [human review](llm_eval_stage2.md) first.

---

## 4. Optional local check (free)

```bash
cd apps/api
source .venv/Scripts/activate
python scripts/run_llm_eval.py --provider fake \
  --dataset-version pilot --suites ru_esuy_judge_v1 \
  --output-dir evals/reports/pilot-2026-10/stage1-reopen
```

---

## 5. Related

Human Experiment 1 dataset: [llm_eval_stage2.md](llm_eval_stage2.md) (`esuy_ru_human_v1`) — **owner review first**.
