"""Render evaluation reports (JSON + Markdown)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = round((p / 100) * (len(ordered) - 1))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def build_summary(case_results: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    latencies = [float(r["latency_ms"]) for r in case_results if r.get("latency_ms") is not None]
    errors = [r for r in case_results if r.get("error")]
    det_pass = [r for r in case_results if r.get("deterministic", {}).get("passed")]
    judge_scores = [
        float(r["judge"]["score"])
        for r in case_results
        if isinstance(r.get("judge"), dict) and "score" in r["judge"]
    ]
    return {
        "meta": {
            **meta,
            "generated_at": datetime.now(UTC).isoformat(),
            "case_count": len(case_results),
        },
        "measured": {
            "deterministic_pass_rate": (len(det_pass) / len(case_results)) if case_results else 0.0,
            "deterministic_passed": len(det_pass),
            "error_count": len(errors),
            "error_rate": (len(errors) / len(case_results)) if case_results else 0.0,
            "latency_ms_p50": percentile(latencies, 50),
            "latency_ms_p95": percentile(latencies, 95),
            "latency_ms_mean": (sum(latencies) / len(latencies)) if latencies else None,
            "judge_score_mean": (sum(judge_scores) / len(judge_scores)) if judge_scores else None,
            "judge_cases": len(judge_scores),
        },
        "cases": case_results,
    }


def write_report(summary: dict[str, Any], output_dir: Path, stem: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    return json_path, md_path


def render_markdown(summary: dict[str, Any]) -> str:
    meta = summary.get("meta") or {}
    measured = summary.get("measured") or {}
    lines = [
        f"# Decime LLM eval report - {meta.get('dataset_version', 'v1')}",
        "",
        "## Meta (conditions)",
        "",
        f"- Generated: `{meta.get('generated_at')}`",
        f"- Provider: `{meta.get('provider')}`",
        f"- Orchestrator: `{meta.get('orchestrator')}`",
        f"- Model: `{meta.get('model')}`",
        f"- Suites: `{meta.get('suites')}`",
        f"- Judge enabled: `{meta.get('judge_enabled')}`",
        f"- Cases: `{meta.get('case_count')}`",
        "",
        "## Measured results",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Deterministic pass rate | {measured.get('deterministic_pass_rate'):.2%} |",
        f"| Deterministic passed | {measured.get('deterministic_passed')} |",
        f"| Error rate | {measured.get('error_rate'):.2%} |",
        f"| Latency p50 (ms) | {measured.get('latency_ms_p50')} |",
        f"| Latency p95 (ms) | {measured.get('latency_ms_p95')} |",
        f"| Judge mean score | {measured.get('judge_score_mean')} |",
        "",
        "## Interpretation notes",
        "",
        "- Deterministic metrics are **measured** against suite `expect` rules.",
        "- Judge scores (if present) are **LLM opinions**, not ground truth.",
        "- Fake provider results validate wiring; they are **not** quality claims for production models.",
        "",
        "## Failed / errored cases",
        "",
    ]
    failures = [
        c
        for c in summary.get("cases") or []
        if c.get("error") or not (c.get("deterministic") or {}).get("passed")
    ]
    if not failures:
        lines.append("_None._")
    else:
        for case in failures:
            lines.append(
                f"- `{case.get('id')}` suite=`{case.get('suite')}` "
                f"failed={case.get('deterministic', {}).get('failed')} "
                f"error={case.get('error')!r}"
            )
    lines.append("")
    return "\n".join(lines)
