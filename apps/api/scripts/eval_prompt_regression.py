"""Write a prompt-comparison plan. Does not call a model.

    python scripts/eval_prompt_regression.py --commit-a <hash> --commit-b <hash>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from decime_api.evals.prompt_regression import build_regression_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a prompt A/B comparison")
    parser.add_argument("--dataset", default="ru_esuy_judge_v1")
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--prompt-id", default="decime-translate-esuy")
    parser.add_argument("--commit-a", required=True)
    parser.add_argument("--commit-b", required=True)
    args = parser.parse_args()
    plan = build_regression_plan(
        dataset=args.dataset,
        model=args.model,
        prompt_id=args.prompt_id,
        commit_a=args.commit_a,
        commit_b=args.commit_b,
    )
    print(json.dumps(plan, indent=2))
    if os_eval_requested():
        raise SystemExit(
            "DECIME_RUN_EVAL is set, but this script does not spend on model calls. "
            "Run the existing eval runner only after choosing a commit pin."
        )


def os_eval_requested() -> bool:
    import os

    return os.environ.get("DECIME_RUN_EVAL") == "1"


if __name__ == "__main__":
    main()
