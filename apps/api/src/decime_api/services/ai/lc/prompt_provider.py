"""Load a fixed prompt version once per process.

``DECIME_PROMPT_SOURCE=local`` (default) renders the checked-in markdown and the
human templates in ``prompt_templates.py``. No LangSmith call is made.

``DECIME_PROMPT_SOURCE=langsmith`` resolves the environment tag to a commit hash
at startup, then reuses that template. A snapshot is used only when it is the
same commit. A different snapshot is never substituted.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from decime_api.config import settings
from decime_api.services.ai.lc.prompt_hub import (
    PromptConfigError,
    pull_template,
    resolve_commit,
)
from decime_api.services.ai.lc.prompt_templates import (
    PROMPT_IDS,
    missing_variables,
    render_template,
    schema_sha256,
    template_content_sha256,
    template_from_snapshot_manifest,
    template_snapshot_manifest,
)
from decime_api.services.ai.llm_json_schemas import (
    extraction_bundle_json_schema,
    normalize_dictionary_item_json_schema,
    reply_bundle_json_schema,
    understand_text_json_schema,
)

logger = logging.getLogger(__name__)

_SCHEMA_BUILDERS = {
    "translate_to_esuy": reply_bundle_json_schema,
    "understand_incoming": understand_text_json_schema,
    "extract_candidates": extraction_bundle_json_schema,
    "normalize_dictionary_row": normalize_dictionary_item_json_schema,
}

_DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parents[3] / "prompts" / "snapshots"
_LOCK = threading.Lock()
_CACHE: dict[str, LoadedPrompt] = {}
_CLIENT_FACTORY: Any = None
_WARMED = False


@dataclass(frozen=True)
class LoadedPrompt:
    operation: str
    prompt_id: str
    template: ChatPromptTemplate
    prompt_sha256: str
    schema_sha256: str
    prompt_source: str
    code_revision: str
    prompt_environment: str | None = None
    prompt_commit: str | None = None

    def tracing_metadata(self, *, model: str) -> dict[str, str]:
        """Identifiers only. User text stays in the prompt body, not metadata."""
        data = {
            "prompt_id": self.prompt_id,
            "prompt_sha256": self.prompt_sha256,
            "schema_sha256": self.schema_sha256,
            "model": model,
            "code_revision": self.code_revision,
            "prompt_source": self.prompt_source,
        }
        if self.prompt_environment:
            data["prompt_environment"] = self.prompt_environment
        if self.prompt_commit:
            data["prompt_commit"] = self.prompt_commit
        return data


def snapshot_dir() -> Path:
    configured = (settings.decime_prompt_snapshot_dir or "").strip()
    if configured:
        return Path(configured)
    return _DEFAULT_SNAPSHOT_DIR


def current_code_revision() -> str:
    pinned = (settings.decime_code_revision or os.environ.get("DECIME_CODE_REVISION") or "").strip()
    if pinned:
        return pinned
    root = _git_root()
    if root is None:
        return "unknown"
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    revision = output.strip()
    return revision or "unknown"


def reset_prompt_cache() -> None:
    global _WARMED
    with _LOCK:
        _CACHE.clear()
        _WARMED = False


def set_prompt_client_factory(factory: Any) -> None:
    """Test hook. ``None`` restores the real LangSmith client."""
    global _CLIENT_FACTORY
    _CLIENT_FACTORY = factory


def warm_prompt_cache() -> dict[str, LoadedPrompt]:
    """Resolve every production prompt once. Safe to call again; the cache sticks."""
    global _WARMED
    with _LOCK:
        if _WARMED and len(_CACHE) == len(PROMPT_IDS):
            return dict(_CACHE)
        for operation in PROMPT_IDS:
            _CACHE[operation] = _load_uncached(operation)
        _WARMED = True
        return dict(_CACHE)


def get_prompt(operation: str) -> LoadedPrompt:
    if operation not in PROMPT_IDS:
        raise PromptConfigError(f"Unknown prompt operation {operation!r}")
    with _LOCK:
        cached = _CACHE.get(operation)
        if cached is not None:
            return cached
        loaded = _load_uncached(operation)
        _CACHE[operation] = loaded
        return loaded


def render_prompt(operation: str, **variables: Any) -> tuple[str, str, LoadedPrompt]:
    loaded = get_prompt(operation)
    system, human = render_template(loaded.template, variables)
    return system, human, loaded


def system_prompt_text(operation: str) -> str:
    system, _human, _loaded = render_prompt(operation, **_empty_variables(operation))
    return system


def prompt_health_fields() -> dict[str, str]:
    loaded = warm_prompt_cache()
    commits = [
        f"{item.operation}={item.prompt_commit or item.prompt_source}:{item.prompt_sha256[:12]}"
        for item in loaded.values()
    ]
    return {
        "prompt_source": settings.decime_prompt_source,
        "prompt_env": settings.decime_prompt_env,
        "prompt_commits": ",".join(commits),
    }


def eval_prompt_metadata() -> dict[str, Any]:
    """Metadata for a new eval run. Does not rewrite historical reports."""
    loaded = warm_prompt_cache()
    prompts = {}
    for operation, item in loaded.items():
        prompts[operation] = {
            "prompt_id": item.prompt_id,
            "prompt_commit": item.prompt_commit,
            "prompt_sha256": item.prompt_sha256,
            "schema_sha256": item.schema_sha256,
            "prompt_source": item.prompt_source,
            "prompt_environment": item.prompt_environment,
        }
    return {
        "code_revision": current_code_revision(),
        "prompt_source": settings.decime_prompt_source,
        "prompts": prompts,
        "historical_prompt_commit": "legacy_unknown",
        "judge_prompt_version": "not_versioned",
    }


def write_snapshot(loaded: LoadedPrompt, *, captured_at: str | None = None) -> Path:
    if not loaded.prompt_commit:
        raise PromptConfigError(
            f"Refusing to snapshot {loaded.prompt_id} without a LangSmith commit hash"
        )
    directory = snapshot_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{loaded.prompt_id}.json"
    payload = {
        "prompt_id": loaded.prompt_id,
        "operation": loaded.operation,
        "commit_hash": loaded.prompt_commit,
        "content_sha256": loaded.prompt_sha256,
        "captured_at": captured_at or datetime.now(UTC).isoformat(),
        "manifest": template_snapshot_manifest(loaded.template),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _load_uncached(operation: str) -> LoadedPrompt:
    prompt_id = PROMPT_IDS[operation]
    schema_hash = schema_sha256(_SCHEMA_BUILDERS[operation]())
    revision = current_code_revision()
    if settings.decime_prompt_source == "local":
        from decime_api.services.ai.lc.prompt_templates import build_local_template

        template = _validate(operation, build_local_template(operation))
        return LoadedPrompt(
            operation=operation,
            prompt_id=prompt_id,
            template=template,
            prompt_sha256=template_content_sha256(template),
            schema_sha256=schema_hash,
            prompt_source="local",
            code_revision=revision,
            prompt_environment=None,
            prompt_commit=None,
        )
    if settings.decime_prompt_source != "langsmith":
        raise PromptConfigError(
            f"DECIME_PROMPT_SOURCE must be local or langsmith, got {settings.decime_prompt_source!r}"
        )
    return _load_langsmith(operation, prompt_id, schema_hash, revision)


def _load_langsmith(
    operation: str,
    prompt_id: str,
    schema_hash: str,
    revision: str,
) -> LoadedPrompt:
    pin = _pins().get(prompt_id)
    environment = None if pin else settings.decime_prompt_env.strip() or "production"
    ref = pin or environment
    if not ref:
        raise PromptConfigError(f"No environment or commit pin for {prompt_id}")
    client = _client()
    try:
        commit = resolve_commit(client, prompt_id, ref)
    except PromptConfigError:
        if not pin:
            raise
        logger.warning(
            "LangSmith unavailable for pinned prompt %s commit %s; trying snapshot",
            prompt_id,
            pin,
        )
        return _from_snapshot(
            operation,
            prompt_id,
            pin,
            schema_hash,
            revision,
            prompt_environment="pinned",
        )
    try:
        template = pull_template(client, prompt_id, commit)
    except PromptConfigError:
        logger.warning(
            "LangSmith template pull failed for %s@%s; trying matching snapshot",
            prompt_id,
            commit,
        )
        return _from_snapshot(
            operation,
            prompt_id,
            commit,
            schema_hash,
            revision,
            prompt_environment="pinned" if pin else environment,
        )
    template = _validate(operation, template)
    return LoadedPrompt(
        operation=operation,
        prompt_id=prompt_id,
        template=template,
        prompt_sha256=template_content_sha256(template),
        schema_sha256=schema_hash,
        prompt_source="langsmith",
        code_revision=revision,
        prompt_environment="pinned" if pin else environment,
        prompt_commit=commit,
    )


def _from_snapshot(
    operation: str,
    prompt_id: str,
    commit_hash: str,
    schema_hash: str,
    revision: str,
    *,
    prompt_environment: str | None,
) -> LoadedPrompt:
    path = snapshot_dir() / f"{prompt_id}.json"
    if not path.is_file():
        raise PromptConfigError(
            f"LangSmith prompt {prompt_id}@{commit_hash} is unavailable and "
            f"no snapshot exists at {path}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PromptConfigError(f"Snapshot {path} is not valid JSON: {error}") from error
    stored_commit = payload.get("commit_hash")
    if stored_commit != commit_hash:
        raise PromptConfigError(
            f"Snapshot {path} is commit {stored_commit}, not requested {commit_hash}. "
            "Decime will not substitute a different prompt version."
        )
    try:
        template = template_from_snapshot_manifest(payload["manifest"])
    except (TypeError, ValueError, KeyError) as error:
        raise PromptConfigError(f"Snapshot {path} manifest cannot be loaded: {error}") from error
    if not isinstance(template, ChatPromptTemplate):
        raise PromptConfigError(f"Snapshot {path} is not a ChatPromptTemplate")
    template = _validate(operation, template)
    actual_hash = template_content_sha256(template)
    expected_hash = payload.get("content_sha256")
    if expected_hash != actual_hash:
        raise PromptConfigError(
            f"Snapshot {path} hash mismatch: file says {expected_hash}, template is {actual_hash}"
        )
    return LoadedPrompt(
        operation=operation,
        prompt_id=prompt_id,
        template=template,
        prompt_sha256=actual_hash,
        schema_sha256=schema_hash,
        prompt_source="local_snapshot",
        code_revision=revision,
        prompt_environment=prompt_environment,
        prompt_commit=commit_hash,
    )


def _validate(operation: str, template: ChatPromptTemplate) -> ChatPromptTemplate:
    missing = missing_variables(template, operation)
    if missing:
        raise PromptConfigError(
            f"Prompt for {operation} is missing template variables: {', '.join(missing)}"
        )
    return template


def _pins() -> dict[str, str]:
    raw = (settings.decime_prompt_pins or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise PromptConfigError(f"DECIME_PROMPT_PINS is not JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise PromptConfigError("DECIME_PROMPT_PINS must be a JSON object of prompt id to commit")
    pins: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            raise PromptConfigError("DECIME_PROMPT_PINS values must be non-empty commit strings")
        pins[key] = value.strip()
    return pins


def _client() -> Any:
    if _CLIENT_FACTORY is not None:
        return _CLIENT_FACTORY()
    key = (
        settings.langsmith_api_key
        or os.environ.get("LANGSMITH_API_KEY")
        or os.environ.get("LANGCHAIN_API_KEY")
        or ""
    ).strip()
    if not key:
        raise PromptConfigError(
            "DECIME_PROMPT_SOURCE=langsmith requires LANGSMITH_API_KEY. "
            "Local mode does not."
        )
    os.environ["LANGSMITH_API_KEY"] = key
    from langsmith import Client

    return Client(api_key=key)


def _empty_variables(operation: str) -> dict[str, Any]:
    if operation == "translate_to_esuy":
        return {"reinforce_spanish": False, "level_is_a2": False, "payload_json": "{}"}
    if operation == "understand_incoming":
        return {"target_is_ru": True, "payload_json": "{}"}
    return {"payload_json": "{}"}


def _git_root() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return None
