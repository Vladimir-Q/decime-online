# Report 4 — Methodology summary

**Pilot:** Decime UY LLM evaluation (2026-10)  
**Status:** Complete  
**Language:** English  
**Spec:** `docs/llm_eval_pilot_spec.md`

> This report closes the four-artifact pilot. Reports 1–2 are **real** evaluations.  
> Report 3 is **simulated** and must never be cited as production model evidence.

---

## 1. Engineering narrative (what this demonstrates)

| Skill area | What we shipped |
|------------|-----------------|
| Eval design | Two complementary experiments (human pairwise + LLM-as-a-Judge) on harder, owner-approved datasets |
| LLMOps | LangChain Structured Outputs, LangSmith Datasets/Experiments, Pairwise Annotation Queue, usage/cost metadata on replay |
| Experimental hygiene | Stable `case_id`, A/B model roles, pair-integrity check before annotation, no temperature hardcoding for Luna |
| Statistics | Win/tie rates, sign test, bootstrap CIs, Monte Carlo power — with explicit real vs synthetic separation |
| Product constraint | Uruguay/Montevideo locale; prod-shaped translate/understand payloads only |

---

## 2. Design overview

```text
Owner-approved JSONL (pilot/)
  → Decime eval runner (LangChain ChatOpenAI)
  → LangSmith experiments (A = gpt-5.6-luna, B = gpt-6-luna)
        ├─ Exp 1: PAQ human labels (es-UY → RU)
        └─ Exp 2: gpt-5-mini Structured judge (RU → es-UY)
  → Reports 1–2 (real)
  → Synthetic 400+400 → Report 3 (simulated)
  → Report 4 (this document)
```

### Experiments

| | Experiment 1 (human) | Experiment 2 (judge) |
|--|----------------------|----------------------|
| Direction | es-UY → RU (`understand_incoming`) | RU → es-UY (`translate_to_esuy`) |
| Dataset | `esuy_ru_human_v1` (n=30) | `ru_esuy_judge_v1` (n=30) |
| Candidates | A/B Luna models | Same A/B |
| Scoring | Pairwise A/B/Equal | 1–5 × 4 criteria + critical/rationale |
| Tooling | LangSmith PAQ | Decime `judge_pilot` + Stage 5 CLI |

### Owner locks that changed the original 4-criterion human plan

- Human annotation used **one criterion only:** Style Preservation (`style preservation`).
- Prod text default after the pilot pairwise: **`gpt-6-luna`** (`OPENAI_TEXT_MODEL`).

---

## 3. LLMOps pipeline (how it works)

1. **Stage 0** — model probe + budget check (USD 4 ceiling).
2. **Stages 1–2** — owner review of Excel/JSONL drafts before any paid bulk run.
3. **Stage 3** — dual-model runs; LangSmith upload replays local outputs keyed by `case_id`; attaches token/cost `usage_metadata` on a child `run_type=llm` span.
4. **Stage 4** — `eval_stage4_pair_check.py` verifies local id sets **and** LangSmith chronological order (PAQ pairs by time, not by id).
5. **Stage 5** — Structured judge (`gpt-5-mini`); dry-run gate then full 60 calls; scores as LangSmith feedback.
6. **Reports 1–3** — export/aggregate scripts under `apps/api/scripts/eval_report*.py`.
7. **Production** — text path remains replaceable via `OPENAI_TEXT_MODEL`; VM tracing stays off.

Key scripts:

| Script | Role |
|--------|------|
| `eval_stage3_ab.py` | A/B translate/understand → LangSmith |
| `eval_stage4_pair_check.py` | Pair integrity |
| `eval_stage5_judge.py` | LLM judge dry-run / full |
| `eval_report1_human.py` | PAQ → Report 1 |
| `eval_report2_judge.py` | Stage 5 → Report 2 |
| `eval_report3_synthetic.py` | Simulations → Report 3 |

---

## 4. Real results (summary)

### Report 1 — Human pairwise (style)

| | A `gpt-5.6-luna` | B `gpt-6-luna` | Equal |
|--|------------------|----------------|-------|
| Wins | 9 | **18** | 0 |

**Winner (style):** B / `gpt-6-luna` (60%).

### Report 2 — LLM-as-a-Judge

| Criterion (mean) | A | B |
|------------------|---|---|
| Semantic Fidelity | 4.800 | **4.833** |
| UY Naturalness | 4.433 | **4.467** |
| Style Preservation | 4.700 | **4.933** |
| No Add/Omit | 4.800 | **4.867** |

Paired SF: A better 3 · B better 4 · Equal **23**. Critical errors: 0/0.  
Judge cost ≈ **USD 0.112**.

**Interpretation:** On meaning, models are close (many ties). Humans and the judge both favor **B on style**; that aligns with promoting `gpt-6-luna` for prod text.

---

## 5. Simulated results (Report 3) — limitations

- Small-effect multinomial / paired-score generators with fixed seeds.
- Sign-test **power ≈ 0.05 at N=30** → real pilot is exploratory, not confirmatory.
- Power ≈ 0.46 at synthetic N=400 still below 80% target for this effect size.
- Null simulation at N=400 ≈ 0.05 → type-I control looks sane.

**Do not** merge synthetic N=400 into claims about production quality.

---

## 6. Budget & auditability

| Item | Note |
|------|------|
| Ceiling | USD 4 hard stop |
| Paid blocks | Stage 0 probes + 60+60 translate + 60 judge (+ dry-runs) |
| Observed judge block | ~USD 0.11 |
| Traceability | `case_id`, experiment names, model ids, local JSON reports, LangSmith project `decime-eval-pilot` |

---

## 7. Threats to validity

1. **Single annotator** — no IAA; human Exp 1 is owner preference, not crowd truth.
2. **Single human criterion** — style only; semantic fidelity not human-labeled in Exp 1.
3. **PAQ UI side vs role** — Report 1 maps by experiment/session role, not left/right UI chrome.
4. **Small N** — underpowered for small effects (see Report 3).
5. **Judge is an LLM** — correlated errors possible; rubric English, outputs es-UY.
6. **Replay experiments** — Stage 3 LangSmith runs do not re-call the model; cost is attached from Decime-captured usage.

---

## 8. Recommendations

1. Keep **`gpt-6-luna`** as default text model (style wins + slight judge edge; cost-efficient).
2. Treat N=30 results as **directional**; expand datasets before claiming significance.
3. If re-running human eval, either restore 4 criteria or explicitly keep style-only in the spec.
4. Optional: re-upload human Stage 3 with cost metadata if PAQ must sit on the latest experiment session (labels today live on `…-2214-…`).

---

## 9. Artifact index

| Report | Path |
|--------|------|
| 1 Human | `apps/api/evals/reports/pilot-2026-10/report1_human/` |
| 2 Judge | `apps/api/evals/reports/pilot-2026-10/report2_judge/` |
| 3 Synthetic | `apps/api/evals/reports/pilot-2026-10/report3_synthetic/` |
| 4 Methodology | `apps/api/evals/reports/pilot-2026-10/report4_methodology/` (this file) |

Doc pointers: `docs/llm_eval_report1.md` … `docs/llm_eval_report4.md`.
