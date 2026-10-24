"""Report 1 human pairwise aggregation (no LLM).

Canonical labels match Report 2 / synthetic sims: ``A_better``, ``B_better``, ``equal``.
Historical exports used title-case ``Equal``; aggregation must normalize that key.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

LABEL_A = "A_better"
LABEL_B = "B_better"
LABEL_EQUAL = "equal"
LABEL_MISSING = "missing"

_LABEL_ALIASES = {
    "a_better": LABEL_A,
    "b_better": LABEL_B,
    "equal": LABEL_EQUAL,
    "missing": LABEL_MISSING,
}


def normalize_label(label: str | None) -> str:
    """Map historical / display variants onto canonical lowercase keys."""
    if label is None:
        return LABEL_MISSING
    key = str(label).strip().lower()
    return _LABEL_ALIASES.get(key, key)


def label_from_scores(score_a: float | None, score_b: float | None) -> str:
    """Map binary pairwise scores → A better / B better / equal."""
    if score_a is None or score_b is None:
        return LABEL_MISSING
    if score_a > score_b:
        return LABEL_A
    if score_b > score_a:
        return LABEL_B
    return LABEL_EQUAL


def normalize_case_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return copies with canonical ``label`` values."""
    out: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        copy["label"] = normalize_label(row.get("label"))
        out.append(copy)
    return out


def aggregate_pairwise_labels(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate normalized labels; rates use labeled pairs only (exclude missing)."""
    normalized = normalize_case_rows(rows)
    counts = Counter(r["label"] for r in normalized)
    labeled = [r for r in normalized if r["label"] != LABEL_MISSING]
    n_labeled = len(labeled)
    n_a = int(counts.get(LABEL_A, 0))
    n_b = int(counts.get(LABEL_B, 0))
    n_eq = int(counts.get(LABEL_EQUAL, 0))
    assert_label_counts_match_n_labeled(
        {LABEL_A: n_a, LABEL_B: n_b, LABEL_EQUAL: n_eq},
        n_labeled,
    )
    primary_winner = (
        "A"
        if n_a > n_b
        else "B"
        if n_b > n_a
        else "tie"
    )
    return {
        "cases": normalized,
        "n_pairs": len(normalized),
        "n_labeled": n_labeled,
        "counts": {
            LABEL_A: n_a,
            LABEL_B: n_b,
            LABEL_EQUAL: n_eq,
            **(
                {LABEL_MISSING: int(counts[LABEL_MISSING])}
                if counts.get(LABEL_MISSING)
                else {}
            ),
        },
        "win_rate_a": round(n_a / n_labeled, 3) if n_labeled else None,
        "win_rate_b": round(n_b / n_labeled, 3) if n_labeled else None,
        "equal_rate": round(n_eq / n_labeled, 3) if n_labeled else None,
        "primary_winner": primary_winner,
    }


def assert_label_counts_match_n_labeled(
    counts: dict[str, int],
    n_labeled: int,
) -> None:
    """Require A + B + Equal == number of labeled pairs."""
    total = (
        int(counts.get(LABEL_A, 0))
        + int(counts.get(LABEL_B, 0))
        + int(counts.get(LABEL_EQUAL, 0))
    )
    if total != n_labeled:
        raise AssertionError(
            f"label counts sum {total} != n_labeled {n_labeled} (counts={counts})"
        )


def rebuild_summary_from_report(summary: dict[str, Any]) -> dict[str, Any]:
    """Recompute counts/rates from saved ``cases`` (no LangSmith / LLM)."""
    cases = list(summary.get("cases") or [])
    agg = aggregate_pairwise_labels(cases)
    rebuilt = dict(summary)
    rebuilt.update(
        {
            "n_pairs": agg["n_pairs"],
            "n_labeled": agg["n_labeled"],
            "counts": agg["counts"],
            "win_rate_a": agg["win_rate_a"],
            "win_rate_b": agg["win_rate_b"],
            "equal_rate": agg["equal_rate"],
            "primary_winner": agg["primary_winner"],
            "cases": agg["cases"],
        }
    )
    return rebuilt
