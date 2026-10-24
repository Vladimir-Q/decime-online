#!/usr/bin/env python3
"""Aggregate Stage 5 LLM-as-a-Judge scores → Report 2.

Reads ``stage5-*-full.json`` (60 judged outputs) and writes JSON/CSV/MD under
``evals/reports/pilot-2026-10/report2_judge/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

CRITERIA = (
    "semantic_fidelity",
    "uy_naturalness",
    "style_preservation",
    "no_additions_omissions",
)
MODEL_A = "gpt-5.6-luna"
MODEL_B = "gpt-6-luna"


def _mean(xs: list[float]) -> float | None:
    return round(statistics.mean(xs), 3) if xs else None


def _paired_winner(score_a: int, score_b: int) -> str:
    if score_a > score_b:
        return "A_better"
    if score_b > score_a:
        return "B_better"
    return "equal"


def main() -> int:
    parser = argparse.ArgumentParser(description="Decime Report 2 — LLM judge aggregation")
    parser.add_argument(
        "--stage5-json",
        default="evals/reports/pilot-2026-10/stage5/stage5-ru_esuy_judge_v1-full.json",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/reports/pilot-2026-10/report2_judge",
    )
    args = parser.parse_args()

    stage5_path = Path(args.stage5_json)
    if not stage5_path.is_file():
        print(f"ERROR: missing {stage5_path}")
        return 1
    raw = json.loads(stage5_path.read_text(encoding="utf-8"))
    cases = [c for c in (raw.get("cases") or []) if "judge" in c and not c.get("error")]

    by_case: dict[str, dict[str, Any]] = {}
    for row in cases:
        cid = row.get("case_id")
        role = row.get("role")
        if not cid or role not in ("A", "B"):
            continue
        by_case.setdefault(str(cid), {})[role] = row

    paired: list[dict[str, Any]] = []
    for cid in sorted(by_case):
        sides = by_case[cid]
        if "A" not in sides or "B" not in sides:
            continue
        ja = sides["A"]["judge"]
        jb = sides["B"]["judge"]
        row: dict[str, Any] = {
            "case_id": cid,
            "model_a": MODEL_A,
            "model_b": MODEL_B,
            "reply_a": sides["A"].get("recommended_reply"),
            "reply_b": sides["B"].get("recommended_reply"),
            "critical_error_a": bool(ja.get("critical_error")),
            "critical_error_b": bool(jb.get("critical_error")),
            "error_category_a": ja.get("error_category"),
            "error_category_b": jb.get("error_category"),
            "rationale_a": ja.get("rationale"),
            "rationale_b": jb.get("rationale"),
            "primary_winner": _paired_winner(
                int(ja["semantic_fidelity"]), int(jb["semantic_fidelity"])
            ),
        }
        for key in CRITERIA:
            row[f"{key}_a"] = int(ja[key])
            row[f"{key}_b"] = int(jb[key])
            row[f"{key}_winner"] = _paired_winner(int(ja[key]), int(jb[key]))
        paired.append(row)

    if len(paired) != 30:
        print(f"WARNING: expected 30 pairs, got {len(paired)}")

    means_a = {k: _mean([p[f"{k}_a"] for p in paired]) for k in CRITERIA}
    means_b = {k: _mean([p[f"{k}_b"] for p in paired]) for k in CRITERIA}
    primary_counts = Counter(p["primary_winner"] for p in paired)
    per_crit_wins = {
        k: dict(Counter(p[f"{k}_winner"] for p in paired)) for k in CRITERIA
    }
    crit_a = sum(1 for p in paired if p["critical_error_a"])
    crit_b = sum(1 for p in paired if p["critical_error_b"])
    cost = sum(
        float((c.get("judge") or {}).get("usage", {}).get("estimated_cost_usd") or 0)
        for c in cases
    )
    cat_a = Counter(p["error_category_a"] for p in paired)
    cat_b = Counter(p["error_category_b"] for p in paired)

    primary_winner = (
        "A"
        if primary_counts["A_better"] > primary_counts["B_better"]
        else "B"
        if primary_counts["B_better"] > primary_counts["A_better"]
        else "tie"
    )

    meta = raw.get("meta") or {}
    summary = {
        "report": 2,
        "title": "LLM-as-a-Judge evaluation (Experiment 2)",
        "generated_at": datetime.now(UTC).isoformat(),
        "suite": "ru_esuy_judge_v1",
        "direction": "RU → es-UY (translate_to_esuy)",
        "judge_model": meta.get("judge_model") or "gpt-5-mini",
        "model_a": MODEL_A,
        "model_b": MODEL_B,
        "source_stage5": str(stage5_path),
        "langsmith": meta.get("langsmith"),
        "n_pairs": len(paired),
        "n_judged_outputs": len(cases),
        "means_a": means_a,
        "means_b": means_b,
        "primary_criterion": "semantic_fidelity",
        "primary_pair_counts": dict(primary_counts),
        "primary_winner": primary_winner,
        "per_criterion_pair_counts": per_crit_wins,
        "critical_error_count_a": crit_a,
        "critical_error_count_b": crit_b,
        "error_category_counts_a": dict(cat_a),
        "error_category_counts_b": dict(cat_b),
        "judge_estimated_cost_usd": round(cost, 6),
        "cases": paired,
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report2_judge.json"
    csv_path = out_dir / "report2_judge.csv"
    md_path = out_dir / "report2_judge.md"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fieldnames = (
        ["case_id", "primary_winner"]
        + [f"{k}_a" for k in CRITERIA]
        + [f"{k}_b" for k in CRITERIA]
        + [f"{k}_winner" for k in CRITERIA]
        + [
            "critical_error_a",
            "critical_error_b",
            "error_category_a",
            "error_category_b",
        ]
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in paired:
            writer.writerow(row)

    def _fmt_means(m: dict[str, float | None]) -> str:
        return ", ".join(f"{k}={v}" for k, v in m.items())

    md_lines = [
        "# Report 2 — LLM-as-a-Judge (Experiment 2)",
        "",
        f"- Suite: `ru_esuy_judge_v1` (RU → es-UY)",
        f"- Judge: `{summary['judge_model']}` (Structured Outputs, 4 criteria 1–5)",
        f"- Model A: `{MODEL_A}` · Model B: `{MODEL_B}`",
        f"- Pairs: **{len(paired)}** (60 judged outputs)",
        f"- Judge cost (est. USD): **{summary['judge_estimated_cost_usd']}**",
        f"- Critical errors: A={crit_a} · B={crit_b}",
        "",
        "## Means by role",
        "",
        f"- A (`{MODEL_A}`): {_fmt_means(means_a)}",
        f"- B (`{MODEL_B}`): {_fmt_means(means_b)}",
        "",
        "## Paired comparison (primary = semantic_fidelity)",
        "",
        f"- A better: **{primary_counts.get('A_better', 0)}**",
        f"- B better: **{primary_counts.get('B_better', 0)}**",
        f"- Equal: **{primary_counts.get('equal', 0)}**",
        f"- Primary winner (count): **{primary_winner}**",
        "",
        "## Paired wins by criterion",
        "",
        "| criterion | A_better | B_better | equal |",
        "|-----------|----------|----------|-------|",
    ]
    for k in CRITERIA:
        c = per_crit_wins[k]
        md_lines.append(
            f"| {k} | {c.get('A_better', 0)} | {c.get('B_better', 0)} | {c.get('equal', 0)} |"
        )
    md_lines.extend(
        [
            "",
            "## Per-case primary (SF)",
            "",
            "| case_id | SF_A | SF_B | winner | UY_A | UY_B |",
            "|---------|------|------|--------|------|------|",
        ]
    )
    for p in paired:
        md_lines.append(
            f"| {p['case_id']} | {p['semantic_fidelity_a']} | {p['semantic_fidelity_b']} | "
            f"{p['primary_winner']} | {p['uy_naturalness_a']} | {p['uy_naturalness_b']} |"
        )
    md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(
        f"pairs={len(paired)} primary_winner={primary_winner} "
        f"SF_means A={means_a['semantic_fidelity']} B={means_b['semantic_fidelity']}"
    )
    print(f"report_json={json_path}")
    print(f"report_csv={csv_path}")
    print(f"report_md={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
