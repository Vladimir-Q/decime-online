"""Dry-run plan for comparing two prompt commits. Does not call a model."""

from __future__ import annotations

from typing import Any


def build_regression_plan(
    *,
    dataset: str,
    model: str,
    prompt_id: str,
    commit_a: str,
    commit_b: str,
) -> dict[str, Any]:
    """Describe a future A/B run. Paid execution stays behind an explicit opt-in."""
    if not commit_a or not commit_b:
        raise ValueError("Both prompt commits are required")
    if commit_a == commit_b:
        raise ValueError("Prompt commits must differ so the comparison isolates the prompt")
    return {
        "dataset": dataset,
        "model": model,
        "prompt_id": prompt_id,
        "commit_a": commit_a,
        "commit_b": commit_b,
        "changed": ["prompt_commit"],
        "held_constant": ["dataset", "model"],
        "metrics": [
            "translation_quality",
            "critical_errors",
            "cost",
            "latency",
            "failing_cases",
        ],
        "paid_execution": False,
        "decision": "not_run",
        "note": (
            "Plan only. Completed October 2026 experiments stay legacy_unknown "
            "and are not recalculated."
        ),
    }
