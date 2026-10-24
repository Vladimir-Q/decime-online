"""Stage 7: synthetic pairwise / judge score simulations (clearly labeled simulated)."""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class HumanSimParams:
    """Multinomial probs for A_better / B_better / Equal (single criterion)."""

    p_a: float
    p_b: float
    p_equal: float
    seed: int
    n: int = 400
    criterion: str = "style_preservation"
    effect: str = "small"


@dataclass(frozen=True)
class JudgeSimParams:
    """Paired 1–5 scores: B ≈ clip(A + bias + noise)."""

    mean_a: float
    bias_b: float
    noise_sd: float
    seed: int
    n: int = 400
    primary: str = "semantic_fidelity"
    effect: str = "small"
    p_critical: float = 0.02


def _multinomial_draw(rng: random.Random, p_a: float, p_b: float, p_eq: float) -> str:
    u = rng.random()
    if u < p_a:
        return "A_better"
    if u < p_a + p_b:
        return "B_better"
    return "equal"


def simulate_human_pairs(params: HumanSimParams) -> list[dict[str, Any]]:
    total = params.p_a + params.p_b + params.p_equal
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"human probs must sum to 1, got {total}")
    rng = random.Random(params.seed)
    rows: list[dict[str, Any]] = []
    for i in range(params.n):
        label = _multinomial_draw(rng, params.p_a, params.p_b, params.p_equal)
        rows.append(
            {
                "sim_id": f"syn-human-{i + 1:04d}",
                "criterion": params.criterion,
                "label": label,
                "simulated": True,
            }
        )
    return rows


def _clip_score(x: float) -> int:
    return max(1, min(5, round(x)))


def simulate_judge_pairs(params: JudgeSimParams) -> list[dict[str, Any]]:
    rng = random.Random(params.seed)
    criteria = (
        "semantic_fidelity",
        "uy_naturalness",
        "style_preservation",
        "no_additions_omissions",
    )
    rows: list[dict[str, Any]] = []
    for i in range(params.n):
        base = rng.gauss(params.mean_a, 0.55)
        row: dict[str, Any] = {
            "sim_id": f"syn-judge-{i + 1:04d}",
            "simulated": True,
            "critical_error_a": rng.random() < params.p_critical,
            "critical_error_b": rng.random() < params.p_critical,
        }
        for key in criteria:
            bias = params.bias_b * (1.35 if key == "style_preservation" else 1.0)
            a = _clip_score(base + rng.gauss(0, params.noise_sd))
            b = _clip_score(base + bias + rng.gauss(0, params.noise_sd))
            row[f"{key}_a"] = a
            row[f"{key}_b"] = b
            if a > b:
                row[f"{key}_winner"] = "A_better"
            elif b > a:
                row[f"{key}_winner"] = "B_better"
            else:
                row[f"{key}_winner"] = "equal"
        row["primary_winner"] = row[f"{params.primary}_winner"]
        rows.append(row)
    return rows


def sign_test_pvalue(n_a: int, n_b: int) -> float:
    """Two-sided sign test p-value (ties already dropped). Exact binomial."""
    n = n_a + n_b
    if n == 0:
        return 1.0
    k = min(n_a, n_b)
    cdf = 0.0
    for i in range(k + 1):
        cdf += math.comb(n, i)
    return min(1.0, 2.0 * cdf / (2**n))


def bootstrap_win_rate_ci(
    labels: list[str],
    *,
    target: Literal["A_better", "B_better"],
    seed: int,
    n_boot: int = 2000,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Return (point, lo, hi) for P(target) among all pairs (ties in denominator)."""
    if not labels:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(labels)
    point = sum(1 for x in labels if x == target) / n
    boots: list[float] = []
    for _ in range(n_boot):
        sample = [labels[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(1 for x in sample if x == target) / n)
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return round(point, 4), round(lo, 4), round(hi, 4)


def summarize_human_sim(rows: list[dict[str, Any]], *, seed: int) -> dict[str, Any]:
    labels = [r["label"] for r in rows]
    counts = Counter(labels)
    n = len(labels)
    n_a, n_b = counts.get("A_better", 0), counts.get("B_better", 0)
    p_a, lo_a, hi_a = bootstrap_win_rate_ci(labels, target="A_better", seed=seed + 1)
    p_b, lo_b, hi_b = bootstrap_win_rate_ci(labels, target="B_better", seed=seed + 2)
    return {
        "n": n,
        "counts": dict(counts),
        "win_rate_a": p_a,
        "win_rate_a_ci95": [lo_a, hi_a],
        "win_rate_b": p_b,
        "win_rate_b_ci95": [lo_b, hi_b],
        "equal_rate": round(counts.get("equal", 0) / n, 4) if n else 0.0,
        "sign_test_pvalue_ties_dropped": round(sign_test_pvalue(n_a, n_b), 6),
        "simulated": True,
    }


def summarize_judge_sim(rows: list[dict[str, Any]], *, primary: str, seed: int) -> dict[str, Any]:
    winners = [r["primary_winner"] for r in rows]
    counts = Counter(winners)
    n = len(rows)
    diffs = [r[f"{primary}_b"] - r[f"{primary}_a"] for r in rows]
    mean_diff = statistics.fmean(diffs) if diffs else 0.0
    rng = random.Random(seed + 3)
    boots = []
    for _ in range(2000):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boots.append(statistics.fmean(sample))
    boots.sort()
    lo, hi = boots[50], boots[1949]
    n_a, n_b = counts.get("A_better", 0), counts.get("B_better", 0)
    return {
        "n": n,
        "primary": primary,
        "pair_counts": dict(counts),
        "mean_score_a": round(statistics.fmean(r[f"{primary}_a"] for r in rows), 3),
        "mean_score_b": round(statistics.fmean(r[f"{primary}_b"] for r in rows), 3),
        "mean_paired_diff_b_minus_a": round(mean_diff, 4),
        "mean_paired_diff_ci95": [round(lo, 4), round(hi, 4)],
        "sign_test_pvalue_ties_dropped": round(sign_test_pvalue(n_a, n_b), 6),
        "critical_rate_a": round(sum(1 for r in rows if r["critical_error_a"]) / n, 4),
        "critical_rate_b": round(sum(1 for r in rows if r["critical_error_b"]) / n, 4),
        "simulated": True,
    }


def monte_carlo_power_sign(
    *,
    p_a: float,
    p_b: float,
    p_equal: float,
    n: int,
    alpha: float = 0.05,
    n_trials: int = 2000,
    seed: int = 0,
) -> float:
    """Power of two-sided sign test (ties dropped)."""
    rng = random.Random(seed)
    wins = 0
    for _ in range(n_trials):
        local = random.Random(rng.randrange(1 << 30))
        n_a = n_b = 0
        for _j in range(n):
            label = _multinomial_draw(local, p_a, p_b, p_equal)
            if label == "A_better":
                n_a += 1
            elif label == "B_better":
                n_b += 1
        if sign_test_pvalue(n_a, n_b) < alpha:
            wins += 1
    return round(wins / n_trials, 4)


# Pilot-calibrated small-effect defaults (shrunk toward null vs real Report 1/2).
HUMAN_SMALL = HumanSimParams(
    p_a=0.38,
    p_b=0.47,
    p_equal=0.15,
    seed=20261017,
    n=400,
    criterion="style_preservation",
    effect="small",
)

JUDGE_SMALL = JudgeSimParams(
    mean_a=4.7,
    bias_b=0.12,
    noise_sd=0.45,
    seed=20261017 + 7,
    n=400,
    primary="semantic_fidelity",
    effect="small",
)
