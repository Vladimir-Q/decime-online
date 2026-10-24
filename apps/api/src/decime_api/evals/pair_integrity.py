"""Stage 4: verify A/B experiment pairs share the same ``case_id`` (not row order).

LangSmith Pairwise Annotation Queues pair runs chronologically across two
experiments. This module checks (1) local Stage 3 reports and (2) optional
LangSmith run lists so owners do not annotate misaligned pairs.
"""

from __future__ import annotations

from typing import Any


def _output_text(row: dict[str, Any]) -> str:
    out = row.get("output") or {}
    for key in ("translation_ru", "translation_en", "recommended_reply"):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def index_report_cases(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map case_id → report row (first wins)."""
    by_id: dict[str, dict[str, Any]] = {}
    for row in report.get("cases") or []:
        cid = row.get("id")
        if not cid:
            continue
        cid = str(cid)
        if cid not in by_id:
            by_id[cid] = row
    return by_id


def check_local_pair(
    *,
    report_a: dict[str, Any],
    report_b: dict[str, Any],
    dataset_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare two Stage 3 reports keyed by case_id.

    Returns a summary dict with per-case rows and ``ok`` bool.
    """
    by_a = index_report_cases(report_a)
    by_b = index_report_cases(report_b)
    ids_a = set(by_a)
    ids_b = set(by_b)
    all_ids = sorted(ids_a | ids_b)

    dataset_by_id: dict[str, dict[str, Any]] = {}
    if dataset_cases:
        for case in dataset_cases:
            cid = case.get("id")
            if cid:
                dataset_by_id[str(cid)] = case

    pairs: list[dict[str, Any]] = []
    for cid in all_ids:
        row_a = by_a.get(cid)
        row_b = by_b.get(cid)
        issues: list[str] = []
        if row_a is None:
            issues.append("missing_in_A")
        if row_b is None:
            issues.append("missing_in_B")
        if row_a and row_a.get("error"):
            issues.append(f"error_A:{row_a['error']}")
        if row_b and row_b.get("error"):
            issues.append(f"error_B:{row_b['error']}")
        text_a = _output_text(row_a) if row_a else ""
        text_b = _output_text(row_b) if row_b else ""
        if row_a and not text_a:
            issues.append("empty_output_A")
        if row_b and not text_b:
            issues.append("empty_output_B")

        source = ""
        if cid in dataset_by_id:
            source = str((dataset_by_id[cid].get("input") or {}).get("source_text") or "")
        elif row_a:
            # Human reports do not embed source; leave empty unless dataset provided.
            source = ""

        pairs.append(
            {
                "case_id": cid,
                "ok": not issues,
                "issues": issues,
                "has_output_a": bool(text_a),
                "has_output_b": bool(text_b),
                "output_a_preview": text_a[:120],
                "output_b_preview": text_b[:120],
                "source_preview": source[:120],
            }
        )

    only_a = sorted(ids_a - ids_b)
    only_b = sorted(ids_b - ids_a)
    ok = all(p["ok"] for p in pairs) and not only_a and not only_b
    return {
        "ok": ok,
        "case_count_a": len(ids_a),
        "case_count_b": len(ids_b),
        "shared_case_count": len(ids_a & ids_b),
        "only_in_a": only_a,
        "only_in_b": only_b,
        "failed_pairs": [p["case_id"] for p in pairs if not p["ok"]],
        "pairs": pairs,
    }


def chronological_case_ids(runs: list[Any]) -> list[str]:
    """Extract case_id sequence in start-time order (LangSmith PAQ pairing order)."""

    def _start(run: Any):
        return getattr(run, "start_time", None) or 0

    ordered = sorted(runs, key=_start)
    ids: list[str] = []
    for run in ordered:
        meta = getattr(run, "metadata", None) or {}
        outputs = getattr(run, "outputs", None) or {}
        inputs = getattr(run, "inputs", None) or {}
        # Prefer target outputs.case_id (experiment root) over child-span metadata.
        cid = outputs.get("case_id") or inputs.get("case_id") or meta.get("decime_case_id")
        if cid:
            ids.append(str(cid))
    return ids


def check_langsmith_chronology(
    *,
    case_ids_a: list[str],
    case_ids_b: list[str],
) -> dict[str, Any]:
    """PAQ pairs by chronology — sequences must match exactly."""
    issues: list[str] = []
    if not case_ids_a:
        issues.append("empty_run_list_A")
    if not case_ids_b:
        issues.append("empty_run_list_B")
    if len(case_ids_a) != len(case_ids_b):
        issues.append(f"length_mismatch:{len(case_ids_a)}!={len(case_ids_b)}")
    mismatches: list[dict[str, Any]] = []
    for i, (a, b) in enumerate(zip(case_ids_a, case_ids_b, strict=False)):
        if a != b:
            mismatches.append({"index": i, "case_id_a": a, "case_id_b": b})
    if mismatches:
        issues.append(f"order_mismatch_count:{len(mismatches)}")
    set_a, set_b = set(case_ids_a), set(case_ids_b)
    if set_a != set_b:
        issues.append("set_mismatch")
    return {
        "ok": not issues,
        "issues": issues,
        "sequence_a": case_ids_a,
        "sequence_b": case_ids_b,
        "order_mismatches": mismatches[:20],
        "only_in_a": sorted(set_a - set_b),
        "only_in_b": sorted(set_b - set_a),
    }


def render_integrity_markdown(summary: dict[str, Any]) -> str:
    """Human-readable Stage 4 integrity report."""
    local = summary.get("local") or {}
    ls = summary.get("langsmith") or {}
    lines = [
        "# Stage 4 — pair integrity",
        "",
        f"- Overall OK: **{summary.get('ok')}**",
        f"- Suite: `{summary.get('suite')}`",
        f"- Experiment A: `{summary.get('experiment_a')}`",
        f"- Experiment B: `{summary.get('experiment_b')}`",
        "",
        "## Local Stage 3 reports",
        "",
        f"- OK: **{local.get('ok')}**",
        f"- Cases A/B/shared: {local.get('case_count_a')} / {local.get('case_count_b')} / {local.get('shared_case_count')}",
        f"- Failed pairs: {local.get('failed_pairs') or 'none'}",
        f"- Only in A: {local.get('only_in_a') or 'none'}",
        f"- Only in B: {local.get('only_in_b') or 'none'}",
        "",
        "| case_id | ok | issues |",
        "|---------|----|--------|",
    ]
    for p in local.get("pairs") or []:
        issues = ", ".join(p.get("issues") or []) or "—"
        lines.append(f"| {p['case_id']} | {p['ok']} | {issues} |")

    lines.extend(
        [
            "",
            "## LangSmith chronology (PAQ pairing order)",
            "",
        ]
    )
    if ls.get("skipped"):
        lines.append(f"- Skipped: {ls['skipped']}")
    else:
        lines.append(f"- OK: **{ls.get('ok')}**")
        lines.append(f"- Issues: {ls.get('issues') or 'none'}")
        if ls.get("order_mismatches"):
            lines.append("")
            lines.append("| index | case_id_A | case_id_B |")
            lines.append("|-------|-----------|-----------|")
            for m in ls["order_mismatches"]:
                lines.append(f"| {m['index']} | {m['case_id_a']} | {m['case_id_b']} |")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    if summary.get("ok"):
        lines.append(
            "Create LangSmith Pairwise Annotation Queue from the two human experiments, "
            "then do 2–3 practice labels. Say **Stage 4 OK** before full annotation."
        )
    else:
        lines.append("Fix mismatches before creating the Pairwise Annotation Queue.")
    lines.append("")
    return "\n".join(lines)
