#!/usr/bin/env python3
"""Stage 5: LLM-as-a-Judge dry-run / full for Experiment 2 (RU→es-UY).

Loads Stage 3 A/B translate reports, scores candidates with gpt-5-mini
Structured Outputs. Default is dry-run of first N cases × both models.

Examples (from apps/api, venv active):

  # Dry-run first 2 cases × A/B (= 4 judge calls)
  python scripts/eval_stage5_judge.py

  # Full 60 (requires --full after owner approved dry-run)
  python scripts/eval_stage5_judge.py --full

Env:
  OPENAI_API_KEY, EVAL_JUDGE_MODEL=gpt-5-mini
  LANGSMITH_API_KEY (optional feedback attach)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_DRY_RUN_MARKER = "stage5-ru_esuy_judge_v1-dry-run.json"


def _safe_print(msg: str) -> None:
    """Print without crashing on Windows cp125x consoles (accents / arrows)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(msg.encode(enc, errors="replace").decode(enc, errors="replace"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Stage 3 manifest missing: {path}. Run eval_stage3_ab.py --suite ru_esuy_judge_v1 first."
        )
    return _load_json(path)


def _cases_by_id(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in (report.get("cases") or []) if row.get("id")}


def _pick_case_ids(cases_a: dict[str, dict], cases_b: dict[str, dict], limit: int | None) -> list[str]:
    ids = [cid for cid in cases_a if cid in cases_b]
    ids.sort()
    if limit is not None:
        return ids[:limit]
    return ids


async def _judge_one(
    *,
    case: dict[str, Any],
    candidate_row: dict[str, Any],
    role: str,
    judge_model: str,
    api_key: str,
    base_url: str | None,
) -> dict[str, Any]:
    from decime_api.evals.judge_pilot import llm_judge_translate_pilot

    inp = case.get("input") or {}
    source_text = str(inp.get("source_text") or "")
    context = dict(inp.get("context") or {})
    reply = str((candidate_row.get("output") or {}).get("recommended_reply") or "")
    judged = await llm_judge_translate_pilot(
        source_text=source_text,
        recommended_reply=reply,
        context=context,
        api_key=api_key,
        model=judge_model,
        base_url=base_url,
    )
    return {
        "case_id": case["id"],
        "role": role,
        "candidate_model": (candidate_row.get("usage") or {}).get("model")
        or candidate_row.get("model"),
        "recommended_reply": reply,
        "source_text": source_text,
        "context": context,
        "judge": judged,
    }


def _write_reports(rows: list[dict[str, Any]], meta: dict[str, Any], out_dir: Path, stem: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fidelity = [r["judge"]["semantic_fidelity"] for r in rows if "judge" in r and "error" not in r]
    cost = sum(
        float((r.get("judge") or {}).get("usage", {}).get("estimated_cost_usd") or 0) for r in rows
    )
    summary = {
        "meta": meta,
        "measured": {
            "judged_count": len(rows),
            "error_count": sum(1 for r in rows if r.get("error")),
            "semantic_fidelity_mean": round(sum(fidelity) / len(fidelity), 3) if fidelity else None,
            "judge_estimated_cost_usd": round(cost, 6),
        },
        "cases": rows,
    }
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        f"# Stage 5 judge — {meta.get('mode')}",
        "",
        f"- Suite: `{meta.get('suite')}`",
        f"- Judge model: `{meta.get('judge_model')}`",
        f"- Cases judged: {summary['measured']['judged_count']}",
        f"- Errors: {summary['measured']['error_count']}",
        f"- Mean semantic_fidelity: {summary['measured']['semantic_fidelity_mean']}",
        f"- Judge cost (est. USD): {summary['measured']['judge_estimated_cost_usd']}",
        "",
        "## Samples",
        "",
    ]
    for row in rows[:8]:
        j = row.get("judge") or {}
        lines.append(
            f"### {row.get('case_id')} role={row.get('role')}\n"
            f"- scores: SF={j.get('semantic_fidelity')} UY={j.get('uy_naturalness')} "
            f"ST={j.get('style_preservation')} NA={j.get('no_additions_omissions')} "
            f"critical={j.get('critical_error')} cat={j.get('error_category')}\n"
            f"- rationale: {j.get('rationale')}\n"
            f"- reply: {row.get('recommended_reply')}\n"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _runs_by_case_id(client: Any, experiment_name: str) -> dict[str, Any]:
    """Map case_id → root experiment run for a LangSmith experiment session."""
    by_case: dict[str, Any] = {}
    # API max page size is 100; paginate via list_runs iterator.
    for run in client.list_runs(project_name=experiment_name):
        meta = getattr(run, "metadata", None) or {}
        outputs = getattr(run, "outputs", None) or {}
        case_id = meta.get("decime_case_id") or outputs.get("case_id")
        if not case_id:
            continue
        case_id = str(case_id)
        # Prefer root / target runs (have case_id in outputs) over child llm spans.
        if case_id not in by_case or outputs.get("case_id"):
            by_case[case_id] = run
    return by_case


def _attach_langsmith_feedback(
    *,
    rows: list[dict[str, Any]],
    experiment_a: str | None,
    experiment_b: str | None,
) -> dict[str, Any]:
    """Best-effort: attach score feedback to experiment runs by case_id."""
    if not experiment_a and not experiment_b:
        return {"attached": 0, "skipped": "no experiments in manifest"}
    try:
        from decime_api.evals.langsmith_pilot import _ensure_langsmith_env
        from langsmith import Client
    except Exception as exc:  # noqa: BLE001
        return {"attached": 0, "skipped": f"import: {exc}"}

    try:
        _ensure_langsmith_env()
        client = Client()
    except Exception as exc:  # noqa: BLE001
        return {"attached": 0, "skipped": str(exc)}

    attached = 0
    missing = 0
    errors: list[str] = []
    score_keys = (
        "semantic_fidelity",
        "uy_naturalness",
        "style_preservation",
        "no_additions_omissions",
    )
    for role, exp_name in (("A", experiment_a), ("B", experiment_b)):
        if not exp_name:
            continue
        try:
            by_case = _runs_by_case_id(client, exp_name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{role}:{exc}")
            continue
        for row in rows:
            if row.get("role") != role or row.get("error"):
                continue
            run = by_case.get(row["case_id"])
            if run is None:
                missing += 1
                continue
            j = row["judge"]
            for key in score_keys:
                try:
                    client.create_feedback(
                        run_id=run.id,
                        key=key,
                        score=float(j[key]),
                        comment=(j.get("rationale") or "") if key == "semantic_fidelity" else None,
                    )
                    attached += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{row['case_id']}/{role}/{key}:{exc}")

    return {"attached": attached, "missing_runs": missing, "errors": errors[:10]}


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Decime eval Stage 5 LLM judge (Exp 2)")
    parser.add_argument("--suite", default="ru_esuy_judge_v1")
    parser.add_argument(
        "--manifest",
        default="evals/reports/pilot-2026-10/stage3/stage3-ru_esuy_judge_v1-manifest.json",
    )
    parser.add_argument("--dataset-version", default="pilot")
    parser.add_argument(
        "--dry-run",
        type=int,
        default=2,
        metavar="N",
        help="Judge first N cases × A/B (default 2). Ignored with --full.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Judge all cases × A/B (60). Requires prior dry-run artifact.",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/reports/pilot-2026-10/stage5",
    )
    parser.add_argument(
        "--skip-langsmith-feedback",
        action="store_true",
        help="Do not attach scores to LangSmith experiment runs",
    )
    args = parser.parse_args()

    from decime_api.config import settings
    from decime_api.evals.dataset import load_cases

    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY required")
        return 1

    judge_model = (os.environ.get("EVAL_JUDGE_MODEL") or "gpt-5-mini").strip()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.full:
        marker = out_dir / _DRY_RUN_MARKER
        if not marker.is_file():
            print(
                f"ERROR: --full blocked until dry-run artifact exists: {marker}\n"
                "Run without --full first, then owner-approve."
            )
            return 1
        limit: int | None = None
        mode = "full"
        stem = f"stage5-{args.suite}-full"
    else:
        limit = max(1, int(args.dry_run))
        mode = f"dry-run-{limit}"
        stem = f"stage5-{args.suite}-dry-run"

    manifest = _resolve_manifest(Path(args.manifest))
    report_a = _load_json(Path(manifest["report_a"]))
    report_b = _load_json(Path(manifest["report_b"]))
    by_a = _cases_by_id(report_a)
    by_b = _cases_by_id(report_b)
    case_ids = _pick_case_ids(by_a, by_b, limit)
    if not case_ids:
        print("ERROR: no overlapping case_ids between A and B reports")
        return 1

    dataset_cases = {
        c["id"]: c
        for c in load_cases(version=args.dataset_version, suites=[args.suite])
    }

    _safe_print(
        f"suite={args.suite} mode={mode} judge={judge_model} "
        f"case_ids={len(case_ids)} judge_calls={len(case_ids) * 2}"
    )

    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        case = dataset_cases.get(case_id)
        if case is None:
            rows.append({"case_id": case_id, "error": "missing in dataset"})
            continue
        for role, by_role in (("A", by_a), ("B", by_b)):
            try:
                row = await _judge_one(
                    case=case,
                    candidate_row=by_role[case_id],
                    role=role,
                    judge_model=judge_model,
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_text_base_url,
                )
                rows.append(row)
                j = row["judge"]
                _safe_print(
                    f"  {case_id} {role}: SF={j['semantic_fidelity']} "
                    f"UY={j['uy_naturalness']} ST={j['style_preservation']} "
                    f"NA={j['no_additions_omissions']} crit={j['critical_error']} "
                    f"cat={j['error_category']}"
                )
                _safe_print(f"    rationale: {j['rationale'][:200]}")
            except Exception as exc:  # noqa: BLE001
                rows.append({"case_id": case_id, "role": role, "error": str(exc)})
                _safe_print(f"  {case_id} {role}: ERROR {exc}")

    meta = {
        "stage": 5,
        "mode": mode,
        "suite": args.suite,
        "judge_model": judge_model,
        "model_a": manifest.get("model_a"),
        "model_b": manifest.get("model_b"),
        "case_ids": case_ids,
        "generated_at": datetime.now(UTC).isoformat(),
        "stage3_manifest": str(args.manifest),
        "langsmith": manifest.get("langsmith"),
    }
    json_path, md_path = _write_reports(rows, meta, out_dir, stem)
    print(f"report_json={json_path}")
    print(f"report_md={md_path}")

    if mode.startswith("dry-run"):
        # Canonical marker path used by --full gate.
        marker_path = out_dir / _DRY_RUN_MARKER
        marker_path.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"dry_run_marker={marker_path}")

    feedback_info: dict[str, Any] = {"attached": 0, "skipped": "disabled"}
    if not args.skip_langsmith_feedback:
        ls = manifest.get("langsmith") or {}
        feedback_info = _attach_langsmith_feedback(
            rows=[r for r in rows if "judge" in r],
            experiment_a=ls.get("experiment_a"),
            experiment_b=ls.get("experiment_b"),
        )
        print(f"langsmith_feedback={feedback_info}")

    gate = {
        "stage": 5,
        "mode": mode,
        "report_json": str(json_path),
        "report_md": str(md_path),
        "langsmith_feedback": feedback_info,
        "next": (
            "Owner: inspect dry-run JSON/MD. If OK, say approve full judge "
            "then run: python scripts/eval_stage5_judge.py --full"
            if mode.startswith("dry-run")
            else "Full judge complete — proceed to Report 2 aggregation."
        ),
    }
    gate_path = out_dir / f"stage5-{args.suite}-gate.json"
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"gate={gate_path}")
    print(gate["next"])
    return 1 if any(r.get("error") for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
