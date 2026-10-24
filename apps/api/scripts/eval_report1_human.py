#!/usr/bin/env python3
"""Export Experiment 1 human pairwise labels → Report 1 (single criterion).

Owner locked: one criterion only — ``style preservation``.
Labels live on the first Stage 3 human experiments (…-2214-…).

Rebuild without LangSmith / LLM::

    python scripts/eval_report1_human.py --from-json \\
        evals/reports/pilot-2026-10/report1_human/report1_human.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decime_api.evals.report1_human import (  # noqa: E402
    LABEL_A,
    LABEL_B,
    LABEL_EQUAL,
    aggregate_pairwise_labels,
    label_from_scores,
    rebuild_summary_from_report,
)

# Experiments that received PAQ feedback (first human Stage 3 upload).
DEFAULT_EXP_A = "pilot-esuy_ru_human_v1-A-20261017-2214-4443a5e1"
DEFAULT_EXP_B = "pilot-esuy_ru_human_v1-B-20261017-2214-08a1218c"
CRITERION_KEY = "style preservation"
MODEL_A = "gpt-5.6-luna"
MODEL_B = "gpt-6-luna"


def _case_id_from_run(run: Any) -> str | None:
    outputs = getattr(run, "outputs", None) or {}
    inputs = getattr(run, "inputs", None) or {}
    meta = getattr(run, "metadata", None) or {}
    cid = outputs.get("case_id") or inputs.get("case_id") or meta.get("decime_case_id")
    return str(cid) if cid else None


def _load_runs_by_case(client: Any, experiment_name: str) -> dict[str, Any]:
    by_case: dict[str, Any] = {}
    for run in client.list_runs(project_name=experiment_name):
        cid = _case_id_from_run(run)
        if not cid:
            continue
        outputs = getattr(run, "outputs", None) or {}
        existing = by_case.get(cid)
        if existing is None:
            by_case[cid] = run
            continue
        existing_out = getattr(existing, "outputs", None) or {}
        if outputs.get("case_id") and not existing_out.get("case_id"):
            by_case[cid] = run
    return by_case


def _feedback_by_run(client: Any, run_ids: list[Any], key: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i in range(0, len(run_ids), 40):
        chunk = run_ids[i : i + 40]
        for fb in client.list_feedback(run_ids=chunk, feedback_key=[key]):
            rid = str(fb.run_id)
            out[rid] = fb
    return out


def _write_report(
    summary: dict[str, Any],
    out_dir: Path,
    *,
    experiment_a: str,
    experiment_b: str,
    criterion: str,
) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report1_human.json"
    csv_path = out_dir / "report1_human.csv"
    md_path = out_dir / "report1_human.md"

    rows = list(summary.get("cases") or [])
    counts = summary["counts"]

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "criterion",
                "label",
                "score_a",
                "score_b",
                "model_a",
                "model_b",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in writer.fieldnames})

    md = "\n".join(
        [
            "# Report 1 — Human pairwise (Experiment 1)",
            "",
            f"- Suite: `esuy_ru_human_v1` (es-UY → RU)",
            f"- Criterion (single, owner-locked): **`{criterion}`**",
            f"- Model A: `{MODEL_A}` · Experiment `{experiment_a}`",
            f"- Model B: `{MODEL_B}` · Experiment `{experiment_b}`",
            f"- Labeled pairs: **{summary['n_labeled']}** / {summary['n_pairs']}",
            f"- A better: **{counts.get(LABEL_A, 0)}** ({summary['win_rate_a']})",
            f"- B better: **{counts.get(LABEL_B, 0)}** ({summary['win_rate_b']})",
            f"- Equal: **{counts.get(LABEL_EQUAL, 0)}** ({summary['equal_rate']})",
            f"- Primary winner (count): **{summary['primary_winner']}**",
            "",
            "Role A/B follow experiment metadata (A=`gpt-5.6-luna`, B=`gpt-6-luna`). "
            "PAQ UI left/right may differ if experiments were selected in reverse order — "
            "this report uses session/role mapping, not UI side labels.",
            "",
            "| case_id | label | score_A | score_B |",
            "|---------|-------|---------|---------|",
            *[
                f"| {r['case_id']} | {r['label']} | {r.get('score_a')} | {r.get('score_b')} |"
                for r in rows
            ],
            "",
        ]
    )
    md_path.write_text(md, encoding="utf-8")
    return json_path, csv_path, md_path


def _fetch_rows_from_langsmith(
    *,
    experiment_a: str,
    experiment_b: str,
    criterion: str,
) -> list[dict[str, Any]]:
    from decime_api.evals.langsmith_pilot import _ensure_langsmith_env
    from langsmith import Client

    _ensure_langsmith_env()
    client = Client()

    by_a = _load_runs_by_case(client, experiment_a)
    by_b = _load_runs_by_case(client, experiment_b)
    fb_a = _feedback_by_run(client, [r.id for r in by_a.values()], criterion)
    fb_b = _feedback_by_run(client, [r.id for r in by_b.values()], criterion)

    rows: list[dict[str, Any]] = []
    for cid in sorted(set(by_a) | set(by_b)):
        run_a = by_a.get(cid)
        run_b = by_b.get(cid)
        fa = fb_a.get(str(run_a.id)) if run_a else None
        fb = fb_b.get(str(run_b.id)) if run_b else None
        score_a = float(fa.score) if fa is not None and fa.score is not None else None
        score_b = float(fb.score) if fb is not None and fb.score is not None else None
        out_a = (getattr(run_a, "outputs", None) or {}) if run_a else {}
        out_b = (getattr(run_b, "outputs", None) or {}) if run_b else {}
        rows.append(
            {
                "case_id": cid,
                "criterion": criterion,
                "label": label_from_scores(score_a, score_b),
                "score_a": score_a,
                "score_b": score_b,
                "model_a": MODEL_A,
                "model_b": MODEL_B,
                "translation_a": out_a.get("translation_ru"),
                "translation_b": out_b.get("translation_ru"),
                "run_id_a": str(run_a.id) if run_a else None,
                "run_id_b": str(run_b.id) if run_b else None,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Decime Report 1 — human pairwise export")
    parser.add_argument("--experiment-a", default=DEFAULT_EXP_A)
    parser.add_argument("--experiment-b", default=DEFAULT_EXP_B)
    parser.add_argument("--criterion", default=CRITERION_KEY)
    parser.add_argument(
        "--output-dir",
        default="evals/reports/pilot-2026-10/report1_human",
    )
    parser.add_argument(
        "--from-json",
        default=None,
        help="Rebuild report from saved JSON cases (no LangSmith / LLM).",
    )
    args = parser.parse_args()

    if args.from_json:
        src = Path(args.from_json)
        if not src.is_file():
            print(f"ERROR: missing {src}")
            return 1
        previous = json.loads(src.read_text(encoding="utf-8"))
        summary = rebuild_summary_from_report(previous)
        summary["generated_at"] = datetime.now(UTC).isoformat()
        summary["rebuilt_from"] = str(src).replace("\\", "/")
        experiment_a = str(summary.get("experiment_a") or args.experiment_a)
        experiment_b = str(summary.get("experiment_b") or args.experiment_b)
        criterion = str(summary.get("criterion") or args.criterion)
    else:
        rows = _fetch_rows_from_langsmith(
            experiment_a=args.experiment_a,
            experiment_b=args.experiment_b,
            criterion=args.criterion,
        )
        agg = aggregate_pairwise_labels(rows)
        summary = {
            "report": 1,
            "title": "Human pairwise evaluation (Experiment 1)",
            "generated_at": datetime.now(UTC).isoformat(),
            "suite": "esuy_ru_human_v1",
            "direction": "es-UY → RU (understand_incoming)",
            "criterion": args.criterion,
            "criteria_note": (
                "Owner locked single criterion for this pilot "
                "(not the full 4-criterion rubric)."
            ),
            "experiment_a": args.experiment_a,
            "experiment_b": args.experiment_b,
            "model_a": MODEL_A,
            "model_b": MODEL_B,
            "annotator": "project_owner",
            **{k: agg[k] for k in (
                "n_pairs",
                "n_labeled",
                "counts",
                "win_rate_a",
                "win_rate_b",
                "equal_rate",
                "primary_winner",
                "cases",
            )},
        }
        experiment_a = args.experiment_a
        experiment_b = args.experiment_b
        criterion = args.criterion

    out_dir = Path(args.output_dir)
    json_path, csv_path, md_path = _write_report(
        summary,
        out_dir,
        experiment_a=experiment_a,
        experiment_b=experiment_b,
        criterion=criterion,
    )
    counts = summary["counts"]
    print(
        f"labeled={summary['n_labeled']} A_better={counts.get(LABEL_A, 0)} "
        f"B_better={counts.get(LABEL_B, 0)} equal={counts.get(LABEL_EQUAL, 0)}"
    )
    print(f"primary_winner={summary['primary_winner']}")
    print(f"report_json={json_path}")
    print(f"report_csv={csv_path}")
    print(f"report_md={md_path}")
    return 0 if summary["n_labeled"] == 30 else 1


if __name__ == "__main__":
    raise SystemExit(main())
