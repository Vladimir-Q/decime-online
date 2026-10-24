# Decime — LLM Evaluation Pilot (agreed specification)

**Version:** 1.2 (decisions locked 2026-10-17; pilot executed)  
**Status:** **Pilot complete** — Reports 1–4 under `apps/api/evals/reports/pilot-2026-10/`  
**Language of reports / judge rationale:** English  
**Budget ceiling (paid LLM calls):** **USD 4.00** hard stop

This document freezes the product owner decisions from the review of the 1.0 design brief. Implementation must follow it in **small stages** with a written “how it works” note and manual checkpoints before each paid step.

---

## 1. Goal

Reproducible evaluation of Decime text translation quality using LangChain + LangSmith:

1. Real human pairwise comparison: **es-UY → RU** (30 cases × 2 models).
2. Real LLM-as-a-Judge: **RU → es-UY** (30 cases × 2 models, 60 judged outputs).
3. Two independent statistical simulations × **400** paired observations each.
4. Four separate report artifacts (real vs synthetic clearly separated).

Primary focus: LLM evaluation design, LLMOps, experimental design, statistics.

**Out of scope:** changing production translate business logic, new frontend, n8n, Sheets eval, real 400-case LLM runs, paid CI, continuous production monitoring.

---

## 2. Decisions locked (2026-10-17)

| # | Topic | Decision |
|---|--------|----------|
| 1 | API access | Keys available; **hard budget USD 4** |
| 2 | “Comparable reasoning” for A vs B | Match **token cost / usage envelope** (same prompt, same max output budget, same temperature; record actual tokens) |
| 3 | Judge stack | LangChain `ChatOpenAI` + **Structured Outputs**; model **`gpt-5-mini`** (budget-safe lock) |
| 4 | LangSmith | **Greenfield** — set up workspace/project from scratch |
| 5 | Human pairwise UI | Prefer **LangSmith Pairwise Annotation Queue** |
| 6 | Pair `case_id` check | Automated script **and required** owner visual spot-check in LangSmith UI **before** full human annotation (Stage 4 gate) |
| 7 | Datasets | **New** harder texts (not a rename of old smoke sets) |
| 8 | Dataset authorship | Agent generates drafts; **owner reviews/approves before any paid model run** |
| 9 | Report / rationale language | **English** |
| 10 | Simulation effect size | **Small** effect scenario (plus null for sensitivity as needed) |
| 11 | Viz | CSV export + **Jupyter notebook** for charts |
| 12 | Report paths | `apps/api/evals/reports/pilot-2026-10/` and short pointers under `docs/` |
| 13 | Budget sufficiency | See §8 — **conditional**; gate before paid runs |
| 14 | Next action | Lock this spec in-repo first; then Stage 0 |

### Still required before paid runs (not locked)

| Item | Why |
|------|-----|
| Confirm A/B API IDs in Stage 0 probe | Default below; change only if probe fails |
| LangSmith account + `LANGSMITH_API_KEY` | Greenfield setup in Stage 0/3 |

---

## 3. Models (roles) — locked for USD 4

| Role | API Model ID | Env / flag | Why |
|------|--------------|------------|-----|
| Model A (candidate) | `gpt-5.6-luna` | `EVAL_MODEL_A` | Spec candidate; cheap Luna tier |
| Model B (candidate) | `gpt-6-luna` | `EVAL_MODEL_B` | Spec candidate; cheapest Luna tier |
| **Judge** | **`gpt-5-mini`** | `EVAL_JUDGE_MODEL` | **Budget-safe lock** (see §8) |

**Judge choice (locked):** `gpt-5-mini` — not A, not B (avoids self-grading), supports Structured Outputs via LangChain, ~10× cheaper than `gpt-6.1-sol` on judge volume so the **USD 4 ceiling is hard to miss** even with fat prompts/retries.

**Not used as judge under this budget:** `gpt-6.1-sol` (original “strong judge” idea). It can still fit with Luna A/B (~USD 1 judge block in a mid estimate), but it is **not** the “definitely enough” pick; keep it as an optional upgrade only if Stage 0 shows leftover budget **and** the owner explicitly approves.

All candidate/judge calls go through Decime’s LangChain path (`ChatOpenAI` / optional `OPENAI_TEXT_BASE_URL`). Do **not** rewrite FastAPI product routes for eval.

Generation parameters for A and B are identical and stored in experiment metadata. **Do not pass `temperature=0`:** `gpt-6-luna` only allows the API default — omit temperature for both A and B. Judge may use temperature 0 if supported (`gpt-5-mini`); record actual params in Report 2.

---

## 4. Experiment 1 — Human evaluation (es-UY → RU)

| Field | Value |
|-------|--------|
| Dataset | `esuy_ru_human_v1` — **30** unique Montevideo-oriented Spanish sources |
| Outputs | 60 translations (A+B), 30 pairs |
| Tool | LangSmith Pairwise Annotation Queue |
| Annotator | Project owner (single) — no IAA |
| Labels per criterion | `A better` / `B better` / `Equal` |
| Criteria (original plan) | Semantic Fidelity (**primary**), Russian Naturalness, Nuance Preservation, Style Preservation |
| Criteria (**pilot lock 2026-10-17**) | **Single criterion:** Style Preservation (`style preservation` in LangSmith) — owner decision |
| Blinding | Maximize model-name hiding; document residual UI limitations |

**Stage 4 gate (answers Q6):** before annotation, a script must verify that every pairwise item joins **the same `case_id`** from experiment A and experiment B (not “row order”). Owner spot-checks a few pairs in the LangSmith UI.

---

## 5. Experiment 2 — LLM-as-a-Judge (RU → es-UY)

| Field | Value |
|-------|--------|
| Dataset | `ru_esuy_judge_v1` — **30** unique Russian sources (harder than current smoke `compose_ru_esuy_30`) |
| Compatibility | Input shape must match `translate_to_esuy` / `TranslateToEsRequest` |
| Judge input | Source RU, Spanish candidate, request context, fixed rubric — **no model names** |
| Scales (1–5 each) | Semantic Fidelity (**primary**), Uruguayan Spanish Naturalness, Style Preservation, No Additions/Omissions |
| Extra fields | `critical_error` (bool), `rationale` (EN), `error_category` |
| Rubric | Written and approved before paid judge runs |

Reuse ideas from `compose_ru_esuy_30.jsonl` only as style reference; **do not** treat the old file as the pilot dataset.

**Model-facing context:** prod-only — QR: `whatsapp_text` + optional `user_level` null|`A2`; Live: `in_person` only. No `tone` / `situation` / `output_options`. Dataset `tags`/`tests` are for human review only.

---

## 6. Architecture (target)

```text
Versioned JSONL (new pilot datasets)
        → Decime eval runner (extended)
        → LangChain ChatOpenAI (A / B / Judge)
        → LangSmith Datasets & Experiments
              → Pairwise Annotation Queue (human)
              → Judge runs (auditable)
        → Results + CSV
        → Jupyter (charts) + four reports
        → Separate synthetic simulations (400 + 400)
```

Requirements:

- Reuse Decime LangChain adapters; no production route rewrite.
- No paid evals in default CI.
- Stable links: `case_id`, `run_id`, model id, prompt version, experiment id.
- Never overwrite historical experiment results on re-run (new experiment id / stem).
- Full audit payload retained for restore/replay analysis.

---

## 7. Simulations & statistics

| Simulation | Name | N |
|------------|------|---|
| A (human-like) | `synthetic_human_esuy_ru_400` | 400 pairs, A/B/Equal × 4 criteria |
| B (judge-like) | `synthetic_judge_ru_esuy_400` | 400 pairs, 1–5 × 4 + critical flags |

- Fixed RNG seeds; store distribution parameters.
- Effect-size scenario: **small** (primary); null/sensitivity as secondary.
- Clearly labeled **simulated** — never claimed as real superiority evidence.
- Methods: win/tie rates, sign test (ties dropped), bootstrap CIs, paired score diffs, critical-error rates, Monte Carlo power/sample-size sensitivity (α=0.05, target power 80%, primary = Semantic Fidelity).
- **Do not** treat N=400 synthetic as enlarging the real N=30 pilot.

Deliverables viz: CSV under the pilot report folder + Jupyter notebook for plots.

---

## 8. Budget (USD 4) — will it be enough?

### Call inventory (paid) — matches the experimental design

Judge is **only** Experiment 2. Experiment 1 is human pairwise; no LLM judge there.

| Step | What | Calls |
|------|------|------:|
| Exp 1 translate | `esuy_ru_human_v1`: 30 sources × models A+B | **60** |
| Exp 1 judge | Human Annotation Queue only | **0** |
| Exp 2 translate | `ru_esuy_judge_v1`: 30 sources × models A+B | **60** |
| Exp 2 judge | Each of the **60** Spanish outputs scored separately | **60** |
| Stage 0 probes / dry-runs | Cap | **≤ 10** |
| **Total** | | **≈ 130–190** |

So: **120 translation** calls + **60 judge** calls (+ probes). Not 60 judge on both datasets, and not “30 judge pairs only” (current design = one judge call per candidate output).

### Cost estimate (OpenAI Standard short-context rates, public pricing page)

Assumptions (pessimistic for prompts): translate ≈ 1 500 in + 500 out; judge ≈ 3 000 in + 800 out; prices $/1M tokens.

| Block | Model | Calls | ≈ USD |
|-------|--------|------:|------:|
| Exp 1+2 translate A | `gpt-5.6-luna` ($0.20 / $1.20) | 60 | ~0.05 |
| Exp 1+2 translate B | `gpt-6-luna` ($0.10 / $0.50) | 60 | ~0.02 |
| Exp 2 judge (**locked**) | `gpt-5-mini` ($0.25 / $2.00) | 60 | ~0.14 |
| Probes / retries buffer | mixed | ≤15 | ~0.20 |
| **Pilot total (order)** | | | **≈ 0.40** |
| Hard ceiling | | | **4.00** |

Same inventory with judge `gpt-6.1-sol` ($2 / $10) instead: judge block alone ≈ **0.8–1.2 USD** (still usually under $4 with Luna A/B), but leaves less room for mistakes — **not** selected as the default.

**Verdict with locked judge `gpt-5-mini`:** USD 4 is **comfortable** (roughly an order of magnitude of headroom under these assumptions). Stage 0 still runs a 1-call probe and records actual tokens before the bulk run.

### Hard gates

1. No bulk paid run without Stage 0 probe log + estimate.  
2. Runner must support `--max-cases` / dry-run and abort when projected spend > remaining budget.  
3. Fake provider remains the default CI path.

---

## 9. Report artifacts

| # | Artifact | Location (planned) |
|---|----------|--------------------|
| 1 | Human Evaluation | `apps/api/evals/reports/pilot-2026-10/report1_human/` (+ short link in `docs/`) |
| 2 | LLM-as-a-Judge | `.../report2_judge/` |
| 3 | Synthetic statistical analysis | `.../report3_synthetic/` (must say *simulated*) |
| 4 | Methodology summary | `.../report4_methodology/` |

Each: machine-readable JSON/CSV + short human summary (EN).

---

## 10. Staged implementation (with manual checks)

| Stage | Work | Owner manual check |
|-------|------|--------------------|
| **0** | Audit + probe + LangSmith greenfield — see [llm_eval_stage0.md](llm_eval_stage0.md) | Confirm probe MD all OK; add LangSmith key |
| **1** | Draft `esuy_ru_human_v1` (30 harder es-UY→RU) — **Experiment 1 first** | Review/edit xlsx **before paid A/B** — [stage2](llm_eval_stage2.md) |
| **2** | Draft / finalize `ru_esuy_judge_v1` (30 harder RU→es-UY) — Experiment 2 | Review/edit xlsx **before paid judge** — [stage1](llm_eval_stage1.md) |
| **3** | Runner: dual-model runs → LangSmith Experiments (no judge yet) | UI: two experiments; ids visible |
| **4** | Pairwise queue + **`case_id` pair integrity script** + 2–3 practice annotations | Confirm pairs align; practice labels OK |
| **5** | Judge rubric + Structured Output schema; dry-run 2 cases | Inspect judge JSON + rationale (EN) |
| **6** | Paid pilots (only if budget gate green) | Spot-check outputs; full annotate Exp 1 |
| **7** | Simulations 400+400, stats, power notebook | Notebook runs; labels say simulated |
| **8** | Four reports finalized | Final read-through |

**Order lock (2026-10-17):** human dataset before judge dataset.

---

## 11. Definition of done

Matches the original readiness checklist: 30+30 valid unique cases; both models run with ids; LangSmith experiments; human A/B/Equal × 4; judge 1–5 × 4 + extras; audit data retained; two reproducible simulations; agreed metrics/CIs; power as sensitivity analysis; reports separate real vs synthetic.

---

## 12. Related existing code (baseline, not the pilot)

| Path | Role today |
|------|------------|
| `apps/api/src/decime_api/evals/runner.py` | Fake/OpenAI suite runner |
| `apps/api/src/decime_api/evals/judge.py` | Legacy single-score judge (raw OpenAI) — **replace for pilot** |
| `apps/api/evals/datasets/v1/compose_ru_esuy_30.jsonl` | Smoke/extended translate set — **not** the pilot dataset |
| `apps/api/scripts/run_llm_eval.py` | CLI entry |

---

## 13. Execution status (2026-10-17)

| Stage / report | Status |
|----------------|--------|
| 0–5 | Done (see `docs/llm_eval_stage*.md`) |
| Report 1 human | Done — style only; B wins 18/30 |
| Report 2 judge | Done — B slight edge; many SF ties |
| Report 3 synthetic | Done — labeled SIMULATED |
| Report 4 methodology | Done — `report4_methodology/` |

Prod text model after pilot: `OPENAI_TEXT_MODEL=gpt-6-luna`.
