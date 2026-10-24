# LLM Eval Pilot — Stage 2 report (Human dataset first)

**Date:** 2026-10-17  
**Status:** **Owner approved** (2026-10-17) — texts accepted; no paid A/B until LangSmith + dual-model wiring (Stage 3+)  

**Spec:** [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md) · Experiment 1 (human pairwise)  
**Order note:** Implementation order follows experiments: **human dataset before judge dataset review**.

---

## 1. What this stage delivered

Harder es-UY → RU dataset for Experiment 1 (human pairwise A vs B):

| Item | Value |
|------|--------|
| Dataset | `esuy_ru_human_v1` |
| Path | `apps/api/evals/datasets/pilot/esuy_ru_human_v1.jsonl` |
| Spreadsheet | `apps/api/evals/datasets/pilot/esuy_ru_human_v1.xlsx` |
| Cases | **30** unique `id`s / unique `source_text`s |
| Operation | `understand_incoming` (`source_language: es`, `target_language: ru`) |
| Channel mix | **25** `whatsapp_text` (QR) · **5** `in_person` (Live) |
| Paid LLM calls | **None** |

---

## 2. Request shape (prod-like)

Matches QR / Live understand calls — see app forms:

```json
{
  "source_text": "…",
  "source_language": "es",
  "target_language": "ru",
  "locale_variant": "es-UY-montevideo",
  "channel": "whatsapp_text"
}
```

Live rows use `"channel": "in_person"`.  
No `tone` / `user_level` / `situation` / `output_options` (not used on this path).

Review-only: `tags`, `tests`.

---

## 3. Owner review (manual)

1. Open **`apps/api/evals/datasets/pilot/esuy_ru_human_v1.xlsx`**.
2. Check each Spanish source:
   - natural Montevideo / rioplatense WhatsApp or spoken Spanish;
   - `channel` matches QR vs Live;
   - no duplicate meaning;
   - hard bits explicit (numbers, dates, hedges, irony).
3. Edit in Excel, import back:

```bash
cd apps/api
source .venv/Scripts/activate
python scripts/eval_dataset_xlsx.py import \
  evals/datasets/pilot/esuy_ru_human_v1.xlsx \
  evals/datasets/pilot/esuy_ru_human_v1.jsonl
```

4. Reply:
   - **“Human Stage OK”** (or **“Stage 2 OK”**) → next: dual-model generation wiring / LangSmith for pairwise (still no bulk until budget gate)
   - **“fix human”** + notes → revise texts

**Do not approve paid A/B translate-to-RU until this review is done.**

---

## 4. Optional free smoke

```bash
cd apps/api
source .venv/Scripts/activate
python scripts/run_llm_eval.py --provider fake \
  --dataset-version pilot --suites esuy_ru_human_v1 \
  --output-dir evals/reports/pilot-2026-10/stage2-human
```

---

## 5. Parallel track

`ru_esuy_judge_v1` (Experiment 2 / LLM-as-a-Judge) remains on disk for later owner review — **after** human dataset is approved, or in parallel if you prefer.
