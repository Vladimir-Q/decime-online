"""Unit tests for Stage 7 synthetic sims."""

from __future__ import annotations

from decime_api.evals.synthetic import (
    HUMAN_SMALL,
    JUDGE_SMALL,
    HumanSimParams,
    sign_test_pvalue,
    simulate_human_pairs,
    simulate_judge_pairs,
    summarize_human_sim,
)


def test_human_sim_reproducible_and_counts() -> None:
    a = simulate_human_pairs(HUMAN_SMALL)
    b = simulate_human_pairs(HUMAN_SMALL)
    assert a == b
    assert len(a) == 400
    assert all(r["simulated"] is True for r in a)
    labels = {r["label"] for r in a}
    assert labels <= {"A_better", "B_better", "equal"}


def test_judge_sim_score_bounds() -> None:
    rows = simulate_judge_pairs(JUDGE_SMALL)
    assert len(rows) == 400
    for r in rows:
        for key in (
            "semantic_fidelity_a",
            "semantic_fidelity_b",
            "style_preservation_a",
            "style_preservation_b",
        ):
            assert 1 <= r[key] <= 5


def test_sign_test_symmetric() -> None:
    assert sign_test_pvalue(10, 10) == 1.0
    assert sign_test_pvalue(20, 0) < 0.001


def test_summarize_human_sim() -> None:
    rows = simulate_human_pairs(
        HumanSimParams(p_a=0.5, p_b=0.5, p_equal=0.0, seed=1, n=100)
    )
    summary = summarize_human_sim(rows, seed=1)
    assert summary["simulated"] is True
    assert summary["n"] == 100
    assert abs(summary["win_rate_a"] + summary["win_rate_b"] - 1.0) < 1e-6
