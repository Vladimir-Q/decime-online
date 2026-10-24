"""Register the current production prompts in a private LangSmith hub.

Does not call a model. Does not move the production tag unless
``--also-tag-production`` is passed.

Usage (from apps/api, venv active):

    python scripts/push_langsmith_prompts.py
    python scripts/push_langsmith_prompts.py --tag-staging
    python scripts/rollback_langsmith_prompt.py decime-translate-esuy <commit> staging
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from decime_api.config import settings
from decime_api.services.ai.lc.prompt_hub import (
    PromptConfigError,
    pull_template,
    resolve_commit,
    tag_commit,
)
from decime_api.services.ai.lc.prompt_provider import (
    LoadedPrompt,
    current_code_revision,
    write_snapshot,
)
from decime_api.services.ai.lc.prompt_templates import (
    PROMPT_IDS,
    build_local_template,
    schema_sha256,
    template_content_sha256,
)
from decime_api.services.ai.llm_json_schemas import (
    extraction_bundle_json_schema,
    normalize_dictionary_item_json_schema,
    reply_bundle_json_schema,
    understand_text_json_schema,
)

_SCHEMAS = {
    "translate_to_esuy": reply_bundle_json_schema,
    "understand_incoming": understand_text_json_schema,
    "extract_candidates": extraction_bundle_json_schema,
    "normalize_dictionary_row": normalize_dictionary_item_json_schema,
}


def _client():
    key = (settings.langsmith_api_key or os.environ.get("LANGSMITH_API_KEY") or "").strip()
    if not key:
        raise SystemExit("LANGSMITH_API_KEY is missing. Nothing was pushed.")
    from langsmith import Client

    return Client(api_key=key)


def _same_text(local_template, remote_template) -> bool:
    return template_content_sha256(local_template) == template_content_sha256(remote_template)


def _ensure_tag(client, prompt_id: str, commit: str, tag: str) -> None:
    """Attach a tag when it is missing. Do not move a tag that already points elsewhere."""
    try:
        current = resolve_commit(client, prompt_id, tag)
    except PromptConfigError:
        tag_commit(client, prompt_id, commit, tag)
        print(f"{prompt_id}: {tag} -> {commit}")
        return
    if current != commit:
        print(f"{prompt_id}: {tag} already points at {current}; left unchanged")
        return
    print(f"{prompt_id}: {tag} already at {commit}")


def push_one(client, operation: str, *, tag_staging: bool, tag_production: bool) -> str:
    prompt_id = PROMPT_IDS[operation]
    local = build_local_template(operation)
    local_hash = template_content_sha256(local)
    existing = None
    try:
        existing = client.get_prompt(prompt_id)
    except Exception as error:  # noqa: BLE001 — missing prompt is not fatal
        print(f"{prompt_id}: lookup failed ({error}); creating")
    commit = getattr(existing, "last_commit_hash", None) if existing is not None else None
    remote = None
    if isinstance(commit, str) and commit:
        try:
            remote = pull_template(client, prompt_id, commit)
        except PromptConfigError as error:
            print(
                f"{prompt_id}: existing commit {commit} cannot be loaded ({error}); "
                "pushing a new commit"
            )
            commit = None
            remote = None
        else:
            if not _same_text(local, remote):
                commit = None
            else:
                print(f"{prompt_id}: latest commit {commit} already matches local template")
    if not commit:
        url = client.push_prompt(
            prompt_id,
            object=local,
            is_public=False,
            description="Decime production baseline. Private. Do not publish to the public hub.",
            commit_tags=["v1-0-0"],
            commit_description="v1.0.0 baseline copied from the checked-in Decime prompts",
        )
        print(f"{prompt_id}: pushed {url}")
        commit = resolve_commit(client, prompt_id, "v1-0-0")
        remote = pull_template(client, prompt_id, commit)
        if not _same_text(local, remote):
            raise PromptConfigError(
                f"Pulled {prompt_id}@{commit} does not match the local template"
            )
    else:
        _ensure_tag(client, prompt_id, commit, "v1-0-0")
    if tag_staging:
        _ensure_tag(client, prompt_id, commit, "staging")
    if tag_production:
        tag_commit(client, prompt_id, commit, "production")
        print(f"{prompt_id}: production -> {commit}")
    loaded = LoadedPrompt(
        operation=operation,
        prompt_id=prompt_id,
        template=local,
        prompt_sha256=local_hash,
        schema_sha256=schema_sha256(_SCHEMAS[operation]()),
        prompt_source="langsmith",
        code_revision=current_code_revision(),
        prompt_commit=commit,
        prompt_environment="staging" if tag_staging else None,
    )
    path = write_snapshot(loaded)
    print(f"{prompt_id}: snapshot {path}")
    return commit


def main() -> None:
    parser = argparse.ArgumentParser(description="Push Decime baseline prompts to LangSmith")
    parser.add_argument(
        "--tag-staging",
        action="store_true",
        help="Point the staging tag at this baseline commit",
    )
    parser.add_argument(
        "--also-tag-production",
        action="store_true",
        help="Also point production at this commit. Requires an explicit owner decision.",
    )
    args = parser.parse_args()
    client = _client()
    for operation in PROMPT_IDS:
        push_one(
            client,
            operation,
            tag_staging=args.tag_staging,
            tag_production=args.also_tag_production,
        )


if __name__ == "__main__":
    main()
