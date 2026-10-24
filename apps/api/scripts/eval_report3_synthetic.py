#!/usr/bin/env python3
"""Stage 7 / Report 3: synthetic 400+400 simulations (SIMULATED — not real evidence)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Decime Report 3 — synthetic sims")
    parser.add_argument(
        "--output-dir",
        default="evals/reports/pilot-2026-10/report3_synthetic",
    )
    args = parser.parse_args()

    from decime_api.evals.synthetic import (
        HUMAN_SMALL,
        JUDGE_SMALL,
        monte_carlo_power_sign,
        simulate_human_pairs,
        simulate_judge_pairs,
        summarize_human_sim,
        summarize_judge_sim,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    human_rows = simulate_human_pairs(HUMAN_SMALL)
    judge_rows = simulate_judge_pairs(JUDGE_SMALL)
    human_sum = summarize_human_sim(human_rows, seed=HUMAN_SMALL.seed)
    judge_sum = summarize_judge_sim(
        judge_rows, primary=JUDGE_SMALL.primary, seed=JUDGE_SMALL.seed
    )

    power_n30 = monte_carlo_power_sign(
        p_a=HUMAN_SMALL.p_a,
        p_b=HUMAN_SMALL.p_b,
        p_equal=HUMAN_SMALL.p_equal,
        n=30,
        seed=99,
    )
    power_n400 = monte_carlo_power_sign(
        p_a=HUMAN_SMALL.p_a,
        p_b=HUMAN_SMALL.p_b,
        p_equal=HUMAN_SMALL.p_equal,
        n=400,
        seed=100,
    )
    # null sensitivity
    power_null_n400 = monte_carlo_power_sign(
        p_a=0.425, p_b=0.425, p_equal=0.15, n=400, seed=101
    )

    summary = {
        "report": 3,
        "title": "Synthetic statistical analysis (SIMULATED)",
        "disclaimer": (
            "All rows are simulated. Do NOT treat N=400 as enlarging the real N=30 pilot. "
            "Not evidence of real model superiority."
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "effect_size_scenario": "small",
        "human_sim": {
            "name": "synthetic_human_esuy_ru_400",
            "params": {
                "p_a": HUMAN_SMALL.p_a,
                "p_b": HUMAN_SMALL.p_b,
                "p_equal": HUMAN_SMALL.p_equal,
                "seed": HUMAN_SMALL.seed,
                "n": HUMAN_SMALL.n,
                "criterion": HUMAN_SMALL.criterion,
            },
            "summary": human_sum,
        },
        "judge_sim": {
            "name": "synthetic_judge_ru_esuy_400",
            "params": {
                "mean_a": JUDGE_SMALL.mean_a,
                "bias_b": JUDGE_SMALL.bias_b,
                "noise_sd": JUDGE_SMALL.noise_sd,
                "seed": JUDGE_SMALL.seed,
                "n": JUDGE_SMALL.n,
                "primary": JUDGE_SMALL.primary,
            },
            "summary": judge_sum,
        },
        "power_sensitivity": {
            "alpha": 0.05,
            "target_power": 0.80,
            "method": "monte_carlo_sign_test_ties_dropped",
            "small_effect_power_n30": power_n30,
            "small_effect_power_n400": power_n400,
            "null_effect_power_n400": power_null_n400,
            "note": "N=30 real pilot is underpowered for small effects; N=400 is synthetic only.",
        },
    }

    json_path = out_dir / "report3_synthetic.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    _write_csv(
        out_dir / "synthetic_human_esuy_ru_400.csv",
        human_rows,
        ["sim_id", "criterion", "label", "simulated"],
    )
    judge_fields = [
        "sim_id",
        "simulated",
        "primary_winner",
        "semantic_fidelity_a",
        "semantic_fidelity_b",
        "uy_naturalness_a",
        "uy_naturalness_b",
        "style_preservation_a",
        "style_preservation_b",
        "no_additions_omissions_a",
        "no_additions_omissions_b",
        "critical_error_a",
        "critical_error_b",
    ]
    _write_csv(out_dir / "synthetic_judge_ru_esuy_400.csv", judge_rows, judge_fields)

    md = "\n".join(
        [
            "# Report 3 — Synthetic statistical analysis",
            "",
            "> **SIMULATED.** Not real model evidence. N=400 does not enlarge the real N=30 pilot.",
            "",
            f"- Effect scenario: **{summary['effect_size_scenario']}**",
            f"- Generated: {summary['generated_at']}",
            "",
            "## Simulation A — human-like (`synthetic_human_esuy_ru_400`)",
            "",
            f"- Params: p_A={HUMAN_SMALL.p_a}, p_B={HUMAN_SMALL.p_b}, p_eq={HUMAN_SMALL.p_equal}, "
            f"seed={HUMAN_SMALL.seed}",
            f"- Criterion: `{HUMAN_SMALL.criterion}`",
            f"- Counts: {human_sum['counts']}",
            f"- Win rate A: {human_sum['win_rate_a']} CI95 {human_sum['win_rate_a_ci95']}",
            f"- Win rate B: {human_sum['win_rate_b']} CI95 {human_sum['win_rate_b_ci95']}",
            f"- Sign test p (ties dropped): {human_sum['sign_test_pvalue_ties_dropped']}",
            "",
            "## Simulation B — judge-like (`synthetic_judge_ru_esuy_400`)",
            "",
            f"- Params: mean_A={JUDGE_SMALL.mean_a}, bias_B={JUDGE_SMALL.bias_b}, "
            f"noise_sd={JUDGE_SMALL.noise_sd}, seed={JUDGE_SMALL.seed}",
            f"- Primary: `{JUDGE_SMALL.primary}`",
            f"- Pair counts: {judge_sum['pair_counts']}",
            f"- Mean SF A/B: {judge_sum['mean_score_a']} / {judge_sum['mean_score_b']}",
            f"- Mean paired diff B−A: {judge_sum['mean_paired_diff_b_minus_a']} "
            f"CI95 {judge_sum['mean_paired_diff_ci95']}",
            f"- Sign test p: {judge_sum['sign_test_pvalue_ties_dropped']}",
            "",
            "## Power sensitivity (sign test, α=0.05)",
            "",
            f"- Small-effect power at **N=30** (real pilot size): **{power_n30}**",
            f"- Small-effect power at **N=400** (synthetic only): **{power_n400}**",
            f"- Null-effect power at N=400 (false positive rate check): **{power_null_n400}**",
            "",
            "Target power 80% is not reached at N=30 under this small-effect multinomial — "
            "consistent with treating the real pilot as exploratory.",
            "",
        ]
    )
    (out_dir / "report3_synthetic.md").write_text(md, encoding="utf-8")

    print(f"human_counts={human_sum['counts']} p={human_sum['sign_test_pvalue_ties_dropped']}")
    print(f"judge_counts={judge_sum['pair_counts']} diff={judge_sum['mean_paired_diff_b_minus_a']}")
    print(f"power_n30={power_n30} power_n400={power_n400} null_n400={power_null_n400}")
    print(f"report_dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
