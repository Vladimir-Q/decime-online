"""Unit tests for Report 1 human pairwise aggregation."""

from __future__ import annotations

import pytest

from decime_api.evals.report1_human import (
    LABEL_A,
    LABEL_B,
    LABEL_EQUAL,
    aggregate_pairwise_labels,
    assert_label_counts_match_n_labeled,
    label_from_scores,
    normalize_label,
    rebuild_summary_from_report,
)


def test_normalize_label_maps_historical_equal() -> None:
    assert normalize_label("equal") == LABEL_EQUAL
    assert normalize_label("Equal") == LABEL_EQUAL
    assert normalize_label("A_better") == LABEL_A
    assert normalize_label("B_better") == LABEL_B


def test_label_from_scores() -> None:
    assert label_from_scores(1.0, 0.0) == LABEL_A
    assert label_from_scores(0.0, 1.0) == LABEL_B
    assert label_from_scores(1.0, 1.0) == LABEL_EQUAL
    assert label_from_scores(None, 1.0) == "missing"


def test_aggregate_counts_sum_equals_n_labeled() -> None:
    rows = (
        [{"label": LABEL_A}] * 9
        + [{"label": LABEL_B}] * 18
        + [{"label": "Equal"}] * 3  # historical title-case
    )
    agg = aggregate_pairwise_labels(rows)
    assert agg["n_labeled"] == 30
    assert agg["counts"][LABEL_A] == 9
    assert agg["counts"][LABEL_B] == 18
    assert agg["counts"][LABEL_EQUAL] == 3
    assert agg["equal_rate"] == 0.1
    assert (
        agg["counts"][LABEL_A]
        + agg["counts"][LABEL_B]
        + agg["counts"][LABEL_EQUAL]
        == agg["n_labeled"]
    )
    assert_label_counts_match_n_labeled(agg["counts"], agg["n_labeled"])


def test_rebuild_summary_fixes_equal_rate_bug() -> None:
    """Reproduce the exported bug: cases say Equal, summary looked up 'equal'."""
    cases = (
        [{"case_id": f"a-{i}", "label": LABEL_A} for i in range(9)]
        + [{"case_id": f"b-{i}", "label": LABEL_B} for i in range(18)]
        + [{"case_id": f"e-{i}", "label": "Equal"} for i in range(3)]
    )
    broken = {
        "n_pairs": 30,
        "n_labeled": 30,
        "counts": {LABEL_A: 9, LABEL_B: 18, "Equal": 3},
        "win_rate_a": 0.3,
        "win_rate_b": 0.6,
        "equal_rate": 0.0,  # bug: looked up counts["equal"]
        "primary_winner": "B",
        "cases": cases,
    }
    fixed = rebuild_summary_from_report(broken)
    assert fixed["counts"][LABEL_EQUAL] == 3
    assert "Equal" not in fixed["counts"]
    assert fixed["equal_rate"] == 0.1
    assert all(c["label"] == LABEL_EQUAL for c in fixed["cases"] if c["case_id"].startswith("e-"))
    assert (
        fixed["counts"][LABEL_A]
        + fixed["counts"][LABEL_B]
        + fixed["counts"][LABEL_EQUAL]
        == fixed["n_labeled"]
        == 30
    )


def test_assert_label_counts_mismatch_raises() -> None:
    with pytest.raises(AssertionError, match="label counts sum"):
        assert_label_counts_match_n_labeled(
            {LABEL_A: 9, LABEL_B: 18, LABEL_EQUAL: 0},
            n_labeled=30,
        )
