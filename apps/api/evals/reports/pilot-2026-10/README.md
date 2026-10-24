# LLM eval pilot, October 2026

This folder is the record of the completed pilot. It is the use-case bundle: datasets in `evals/datasets/pilot/`, write-ups in `docs/llm_eval_report1.md`–`report4.md`, and the scripts that exported the tables.

Do not re-run the paid stages to refresh these files. Prompt commits were not stored; treat them as `legacy_unknown`.

| Path | What it is |
|------|------------|
| `stage0/` | Model probe before the pilot |
| `stage1/`, `stage1-reopen/`, `stage2-human/` | Fake-LLM sanity runs |
| `stage3/` | Real A/B generations, human suite and judge suite, models A and B |
| `stage4/` | Pair integrity for the human labels |
| `stage5/` | LLM-as-a-judge on `ru_esuy_judge_v1` (dry run, gate, full 60) |
| `report1_human/` | Human style labels. B `gpt-6-luna` 18, A `gpt-5.6-luna` 9 |
| `report2_judge/` | Judge scores. Mostly ties; B a small edge |
| `report3_synthetic/` | 400+400 **simulated** rows, not human labels |
| `report4_methodology/` | What is real, what is simulated, what not to claim |

Narrative: [docs/llm_eval_report4.md](../../../../../docs/llm_eval_report4.md).
