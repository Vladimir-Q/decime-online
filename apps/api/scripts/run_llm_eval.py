#!/usr/bin/env python3
"""CLI: run Decime LLM evaluation suites.

Examples (from apps/api):

  # Free / CI-safe (Fake provider)
  python scripts/run_llm_eval.py --provider fake

  # OpenAI / OpenAI-compatible (LangChain ChatOpenAI)
  python scripts/run_llm_eval.py --provider openai --suites compose_ru_esuy

  # Optional paid judge (extra OpenAI cost)
  python scripts/run_llm_eval.py --provider openai --suites compose_ru_esuy --judge
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running without editable install.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Decime LLM evaluation runner")
    parser.add_argument("--provider", choices=["fake", "openai"], default="fake")
    parser.add_argument("--dataset-version", default="v1")
    parser.add_argument(
        "--suites",
        default="",
        help="Comma-separated suite names (default: all)",
    )
    parser.add_argument("--judge", action="store_true", help="Enable paid LLM-as-a-Judge on compose")
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument(
        "--model",
        default="",
        help="Override OpenAI chat model (eval A/B; default OPENAI_TEXT_MODEL)",
    )
    parser.add_argument("--output-dir", default="", help="Report directory (default: evals/reports)")
    args = parser.parse_args()

    from decime_api.evals.runner import run_evaluation

    suites = [s.strip() for s in args.suites.split(",") if s.strip()] or None
    output_dir = Path(args.output_dir) if args.output_dir else None
    summary = await run_evaluation(
        provider=args.provider,
        dataset_version=args.dataset_version,
        suites=suites,
        judge=args.judge,
        judge_model=args.judge_model,
        model=args.model.strip() or None,
        output_dir=output_dir,
    )
    measured = summary["measured"]
    print(
        f"cases={summary['meta']['case_count']} "
        f"det_pass={measured['deterministic_pass_rate']:.0%} "
        f"errors={measured['error_count']} "
        f"p50_ms={measured['latency_ms_p50']} "
        f"report={summary['report_md']}"
    )
    # Non-zero if any deterministic failures or exceptions (useful for local gates).
    if measured["deterministic_pass_rate"] < 1.0 or measured["error_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
