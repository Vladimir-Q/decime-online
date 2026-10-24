#!/usr/bin/env python3
"""Stage 3: dual-model A/B runs + LangSmith experiments (no judge).

Default suite is the approved human dataset (Experiment 1 first).

Examples (from apps/api, Git Bash / venv):

  # Wiring only (Fake + LangSmith upload)
  python scripts/eval_stage3_ab.py --provider fake

  # Paid A/B on human suite (uses EVAL_MODEL_A / EVAL_MODEL_B)
  python scripts/eval_stage3_ab.py --provider openai

Env (local .env):
  LANGSMITH_API_KEY, LANGSMITH_PROJECT=decime-eval-pilot
  OPENAI_API_KEY
  EVAL_MODEL_A=gpt-5.6-luna
  EVAL_MODEL_B=gpt-6-luna
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


async def _run_role(
    *,
    role: str,
    model: str,
    provider: str,
    suite: str,
    dataset_version: str,
    output_dir: Path,
) -> dict:
    from decime_api.evals.runner import run_evaluation

    stem = f"stage3-{suite}-{role}-{provider}"
    summary = await run_evaluation(
        provider=provider,  # type: ignore[arg-type]
        dataset_version=dataset_version,
        suites=[suite],
        model=model if provider == "openai" else None,
        judge=False,
        output_dir=output_dir,
        report_stem=stem,
    )
    summary["role"] = role
    summary["eval_model"] = model
    return summary


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Decime eval Stage 3 A/B → LangSmith")
    parser.add_argument("--provider", choices=["fake", "openai"], default="fake")
    parser.add_argument(
        "--suite",
        default="esuy_ru_human_v1",
        help="Pilot suite (default: human Experiment 1)",
    )
    parser.add_argument("--dataset-version", default="pilot")
    parser.add_argument(
        "--skip-langsmith",
        action="store_true",
        help="Only local reports (no LangSmith upload)",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/reports/pilot-2026-10/stage3",
    )
    args = parser.parse_args()

    model_a = os.environ.get("EVAL_MODEL_A", "gpt-5.6-luna").strip()
    model_b = os.environ.get("EVAL_MODEL_B", "gpt-6-luna").strip()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"suite={args.suite} provider={args.provider} A={model_a} B={model_b}")

    summary_a = await _run_role(
        role="A",
        model=model_a,
        provider=args.provider,
        suite=args.suite,
        dataset_version=args.dataset_version,
        output_dir=output_dir,
    )
    summary_b = await _run_role(
        role="B",
        model=model_b,
        provider=args.provider,
        suite=args.suite,
        dataset_version=args.dataset_version,
        output_dir=output_dir,
    )

    for label, summary in (("A", summary_a), ("B", summary_b)):
        m = summary["measured"]
        print(
            f"role={label} cases={summary['meta']['case_count']} "
            f"errors={m['error_count']} det_pass={m['deterministic_pass_rate']:.0%} "
            f"report={summary['report_md']}"
        )
        if m["error_count"]:
            print(f"ERROR: role {label} had {m['error_count']} case errors — abort LangSmith")
            return 1

    manifest = {
        "stage": 3,
        "generated_at": datetime.now(UTC).isoformat(),
        "suite": args.suite,
        "provider": args.provider,
        "model_a": model_a,
        "model_b": model_b,
        "report_a": summary_a.get("report_json"),
        "report_b": summary_b.get("report_json"),
        "langsmith": None,
    }

    if not args.skip_langsmith:
        from decime_api.evals.dataset import load_cases
        from decime_api.evals.langsmith_pilot import (
            ensure_dataset,
            upload_experiment_from_results,
            _ensure_langsmith_env,
        )

        project = _ensure_langsmith_env()
        cases = load_cases(version=args.dataset_version, suites=[args.suite])
        dataset_name = f"decime-pilot-{args.suite}"
        ensure_dataset(
            dataset_name=dataset_name,
            cases=cases,
            description=f"Decime pilot {args.suite} (Stage 3 inputs)",
        )

        report_a = json.loads(Path(summary_a["report_json"]).read_text(encoding="utf-8"))
        report_b = json.loads(Path(summary_b["report_json"]).read_text(encoding="utf-8"))
        results_a = report_a.get("cases") or []
        results_b = report_b.get("cases") or []
        if not results_a or not results_b:
            raise RuntimeError("Report JSON missing cases[]; check evals/report.py shape")

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
        model_a_label = model_a if args.provider == "openai" else "fake"
        model_b_label = model_b if args.provider == "openai" else "fake"
        exp_a = upload_experiment_from_results(
            dataset_name=dataset_name,
            results=results_a,
            experiment_prefix=f"pilot-{args.suite}-A-{stamp}",
            model=model_a_label,
            metadata={
                "role": "A",
                "model": model_a_label,
                "provider": args.provider,
                "suite": args.suite,
                "decime_stage": 3,
            },
        )
        exp_b = upload_experiment_from_results(
            dataset_name=dataset_name,
            results=results_b,
            experiment_prefix=f"pilot-{args.suite}-B-{stamp}",
            model=model_b_label,
            metadata={
                "role": "B",
                "model": model_b_label,
                "provider": args.provider,
                "suite": args.suite,
                "decime_stage": 3,
            },
        )
        manifest["langsmith"] = {
            "project": project,
            "dataset": dataset_name,
            "experiment_a": getattr(exp_a, "experiment_name", str(exp_a)),
            "experiment_b": getattr(exp_b, "experiment_name", str(exp_b)),
        }
        print(
            f"LangSmith project={project} dataset={dataset_name}\n"
            f"  experiment_a={manifest['langsmith']['experiment_a']}\n"
            f"  experiment_b={manifest['langsmith']['experiment_b']}"
        )

    manifest_path = output_dir / f"stage3-{args.suite}-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
