#!/usr/bin/env python3
"""Stage 4: case_id pair integrity for Experiment 1 human A/B.

Checks local Stage 3 reports and (unless --local-only) LangSmith run
chronology — PAQs pair by start time, so A/B sequences must match.

  python scripts/eval_stage4_pair_check.py
  python scripts/eval_stage4_pair_check.py --local-only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _list_experiment_runs(client: Any, experiment_name: str) -> list[Any]:
    """One run per case_id — prefer experiment target (outputs.case_id)."""
    by_case: dict[str, Any] = {}
    for run in client.list_runs(project_name=experiment_name):
        meta = getattr(run, "metadata", None) or {}
        outputs = getattr(run, "outputs", None) or {}
        inputs = getattr(run, "inputs", None) or {}
        cid = outputs.get("case_id") or inputs.get("case_id") or meta.get("decime_case_id")
        if not cid:
            continue
        cid = str(cid)
        existing = by_case.get(cid)
        if existing is None:
            by_case[cid] = run
            continue
        existing_out = getattr(existing, "outputs", None) or {}
        # Upgrade to target run when we only had a child span before.
        if outputs.get("case_id") and not existing_out.get("case_id"):
            by_case[cid] = run
    return list(by_case.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Decime eval Stage 4 pair integrity")
    parser.add_argument(
        "--manifest",
        default="evals/reports/pilot-2026-10/stage3/stage3-esuy_ru_human_v1-manifest.json",
    )
    parser.add_argument("--dataset-version", default="pilot")
    parser.add_argument("--suite", default="esuy_ru_human_v1")
    parser.add_argument(
        "--output-dir",
        default="evals/reports/pilot-2026-10/stage4",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Skip LangSmith chronology check",
    )
    args = parser.parse_args()

    from decime_api.evals.dataset import load_cases
    from decime_api.evals.pair_integrity import (
        check_langsmith_chronology,
        check_local_pair,
        chronological_case_ids,
        render_integrity_markdown,
    )

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"ERROR: manifest missing: {manifest_path}")
        return 1
    manifest = _load_json(manifest_path)
    report_a = _load_json(Path(manifest["report_a"]))
    report_b = _load_json(Path(manifest["report_b"]))
    dataset_cases = load_cases(version=args.dataset_version, suites=[args.suite])

    local = check_local_pair(
        report_a=report_a,
        report_b=report_b,
        dataset_cases=dataset_cases,
    )

    ls_info: dict[str, Any]
    if args.local_only:
        ls_info = {"skipped": "local-only", "ok": True}
    else:
        try:
            from decime_api.evals.langsmith_pilot import _ensure_langsmith_env
            from langsmith import Client

            _ensure_langsmith_env()
            client = Client()
            ls = manifest.get("langsmith") or {}
            exp_a = ls.get("experiment_a")
            exp_b = ls.get("experiment_b")
            if not exp_a or not exp_b:
                ls_info = {"skipped": "no experiment names in manifest", "ok": False}
            else:
                runs_a = _list_experiment_runs(client, exp_a)
                runs_b = _list_experiment_runs(client, exp_b)
                seq_a = chronological_case_ids(runs_a)
                seq_b = chronological_case_ids(runs_b)
                ls_info = check_langsmith_chronology(case_ids_a=seq_a, case_ids_b=seq_b)
                ls_info["experiment_a"] = exp_a
                ls_info["experiment_b"] = exp_b
                ls_info["run_count_a"] = len(runs_a)
                ls_info["run_count_b"] = len(runs_b)
        except Exception as exc:  # noqa: BLE001
            ls_info = {"skipped": str(exc), "ok": False}

    overall_ok = bool(local.get("ok")) and bool(ls_info.get("ok"))
    ls_meta = manifest.get("langsmith") or {}
    summary = {
        "stage": 4,
        "generated_at": datetime.now(UTC).isoformat(),
        "suite": args.suite,
        "manifest": str(manifest_path),
        "experiment_a": ls_meta.get("experiment_a"),
        "experiment_b": ls_meta.get("experiment_b"),
        "dataset": ls_meta.get("dataset"),
        "ok": overall_ok,
        "local": local,
        "langsmith": ls_info,
        "next": (
            "Create Pairwise Annotation Queue in LangSmith; do 2–3 practice labels; "
            "say Stage 4 OK before full 30-pair annotation."
            if overall_ok
            else "Fix pair mismatches before creating the PAQ."
        ),
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "pair_integrity.json"
    md_path = out_dir / "pair_integrity.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_integrity_markdown(summary), encoding="utf-8")

    print(f"ok={overall_ok}")
    print(f"local_ok={local.get('ok')} shared={local.get('shared_case_count')}")
    print(f"langsmith_ok={ls_info.get('ok')} skipped={ls_info.get('skipped')}")
    print(f"report_json={json_path}")
    print(f"report_md={md_path}")
    print(summary["next"])
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
