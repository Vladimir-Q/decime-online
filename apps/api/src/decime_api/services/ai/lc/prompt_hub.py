"""LangSmith prompt hub calls used by the provider and the push/rollback script.

Runtime code asks for an immutable commit hash. Tag moves (staging, production,
rollback) stay in the operator script so the API process cannot promote a prompt.
"""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate


class PromptConfigError(RuntimeError):
    """The requested prompt version cannot be loaded safely."""


def resolve_commit(client: Any, prompt_id: str, ref: str) -> str:
    """Return the commit hash that ``prompt_id:ref`` points at.

    ``ref`` is an environment tag (``staging``, ``production``), a semver tag,
    or a commit hash. The value stored by Decime is the hash returned by the
    API, not the tag name.
    """
    identifier = f"{prompt_id}:{ref}"
    try:
        pulled = client.pull_prompt_commit(
            identifier,
            include_model=False,
            skip_cache=True,
        )
    except Exception as error:
        raise PromptConfigError(
            f"Could not resolve LangSmith prompt {identifier}: {error}"
        ) from error
    commit = getattr(pulled, "commit_hash", None)
    if not isinstance(commit, str) or not commit.strip():
        raise PromptConfigError(
            f"LangSmith did not return a commit hash for {identifier}"
        )
    return commit.strip()


def pull_template(client: Any, prompt_id: str, commit_hash: str) -> ChatPromptTemplate:
    identifier = f"{prompt_id}:{commit_hash}"
    try:
        prompt = client.pull_prompt(identifier, include_model=False, skip_cache=True)
    except Exception as error:
        raise PromptConfigError(f"Could not pull LangSmith prompt {identifier}: {error}") from error
    if not isinstance(prompt, ChatPromptTemplate):
        raise PromptConfigError(
            f"{identifier} is {type(prompt).__name__}, expected ChatPromptTemplate"
        )
    return prompt


def _commit_row_id(client: Any, prompt_id: str, commit_hash: str) -> str:
    """Tag endpoints want the hub row UUID. Traces keep ``commit_hash``."""
    try:
        rows = client.list_prompt_commits(prompt_id)
    except Exception as error:
        raise PromptConfigError(f"Could not list commits for {prompt_id}: {error}") from error
    for row in rows:
        if getattr(row, "commit_hash", None) == commit_hash:
            row_id = getattr(row, "id", None)
            if row_id:
                return str(row_id)
    raise PromptConfigError(f"No LangSmith commit row for {prompt_id}@{commit_hash}")


def tag_commit(client: Any, prompt_id: str, commit_hash: str, tag: str) -> None:
    """Point a mutable tag at an existing commit.

    LangSmith 0.14 exposes this as ``POST /repos/{owner}/{name}/tags``.
    Tags such as ``staging`` and ``production`` are environment pointers.
    ``v1.0.0`` is a semver label. Experiments should record ``commit_hash``.
    """
    if not tag or not commit_hash:
        raise PromptConfigError("tag and commit_hash are required")
    try:
        prompt = client.get_prompt(prompt_id)
    except Exception as error:
        raise PromptConfigError(f"Could not read prompt {prompt_id}: {error}") from error
    full_name = getattr(prompt, "full_name", None) if prompt is not None else None
    owner = getattr(prompt, "owner", None) if prompt is not None else None
    if isinstance(owner, str) and owner and isinstance(full_name, str) and "/" not in full_name:
        full_name = f"{owner}/{full_name}"
    if not isinstance(full_name, str) or not full_name:
        full_name = f"-/{prompt_id}"
    elif "/" not in full_name:
        # Personal workspace prompts have no owner; the API uses "-".
        full_name = f"-/{full_name}"
    commit_id = _commit_row_id(client, prompt_id, commit_hash)
    response = client.request_with_retries(
        "POST",
        f"/repos/{full_name}/tags",
        json={"tag_name": tag, "commit_id": commit_id},
    )
    raise_for_status = getattr(response, "raise_for_status", None)
    if callable(raise_for_status):
        raise_for_status()
