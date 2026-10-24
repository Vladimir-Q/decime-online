"""Move a LangSmith environment tag to an existing commit. Does not edit prompt text.

Usage (from apps/api):

    python scripts/rollback_langsmith_prompt.py decime-translate-esuy <commit> staging
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from decime_api.config import settings
from decime_api.services.ai.lc.prompt_hub import resolve_commit, tag_commit


def main() -> None:
    parser = argparse.ArgumentParser(description="Point a LangSmith prompt tag at a commit")
    parser.add_argument("prompt_id")
    parser.add_argument("commit_hash")
    parser.add_argument("tag", choices=["staging", "production", "v1-0-0"])
    args = parser.parse_args()
    if args.tag == "production" and os.environ.get("DECIME_CONFIRM_PROMPT_PRODUCTION") != "1":
        raise SystemExit(
            "Refusing to move the production tag. Set DECIME_CONFIRM_PROMPT_PRODUCTION=1 "
            "after the owner confirms."
        )
    key = (settings.langsmith_api_key or os.environ.get("LANGSMITH_API_KEY") or "").strip()
    if not key:
        raise SystemExit("LANGSMITH_API_KEY is missing.")
    from langsmith import Client

    client = Client(api_key=key)
    tag_commit(client, args.prompt_id, args.commit_hash, args.tag)
    resolved = resolve_commit(client, args.prompt_id, args.tag)
    if resolved != args.commit_hash:
        raise SystemExit(
            f"{args.tag} resolved to {resolved}, not the requested {args.commit_hash}"
        )
    print(f"{args.prompt_id}: {args.tag} -> {resolved}")


if __name__ == "__main__":
    main()
