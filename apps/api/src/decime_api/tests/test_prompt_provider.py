"""Deterministic prompt provider tests. No LangSmith or OpenAI network calls."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from decime_api.config import settings
from decime_api.evals.prompt_regression import build_regression_plan
from decime_api.schemas.compose import ReplyContext, TranslateToEsRequest
from decime_api.services.ai.lc.prompt_hub import PromptConfigError, tag_commit
from decime_api.services.ai.lc.prompt_provider import (
    LoadedPrompt,
    get_prompt,
    render_prompt,
    reset_prompt_cache,
    set_prompt_client_factory,
    warm_prompt_cache,
    write_snapshot,
)
from decime_api.services.ai.lc.prompt_templates import (
    PROMPT_IDS,
    build_local_template,
    read_system_markdown,
    template_content_sha256,
)
from decime_api.services.ai.lc.tracing import build_run_config
from decime_api.services.ai.openai_llm import _translate_user_content
from decime_api.tests.test_sheets_job_transitions import _assert_scratch_database


class FakeHub:
    def __init__(self) -> None:
        self.by_name = {
            prompt_id: build_local_template(operation)
            for operation, prompt_id in PROMPT_IDS.items()
        }
        self.commit = "a" * 64
        self.fail_resolve = False
        self.fail_pull = False
        self.bad_template = False
        self.calls: list[tuple[str, str]] = []
        self.tags: list[dict[str, str]] = []

    def list_prompt_commits(self, prompt_identifier: str, **_kwargs: object):
        return [
            SimpleNamespace(
                id="80dd086c-3163-42e9-bae3-762a7ea3fe70",
                commit_hash="abc123def",
            )
        ]

    def pull_prompt_commit(self, identifier: str, **_kwargs: object) -> SimpleNamespace:
        self.calls.append(("resolve", identifier))
        if self.fail_resolve:
            raise ConnectionError("langsmith down")
        _name, ref = identifier.split(":", 1)
        if ref in {"production", "staging", "v1-0-0"}:
            return SimpleNamespace(commit_hash=self.commit)
        return SimpleNamespace(commit_hash=ref)

    def pull_prompt(self, identifier: str, **_kwargs: object) -> ChatPromptTemplate:
        self.calls.append(("pull", identifier))
        if self.fail_pull:
            raise ConnectionError("langsmith down")
        name, _commit = identifier.split(":", 1)
        if self.bad_template:
            return ChatPromptTemplate.from_messages(
                [SystemMessage(content="x"), ("human", "{{{payload_json}}}")],
                template_format="mustache",
            )
        return self.by_name[name]

    def get_prompt(self, prompt_id: str) -> SimpleNamespace:
        return SimpleNamespace(full_name=f"owner/{prompt_id}")

    def request_with_retries(self, method: str, path: str, json: dict[str, str] | None = None):
        self.tags.append({"method": method, "path": path, **(json or {})})
        return SimpleNamespace(raise_for_status=lambda: None)


@pytest.fixture(autouse=True)
def _reset_prompts(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "decime_prompt_source", "local")
    monkeypatch.setattr(settings, "decime_prompt_env", "production")
    monkeypatch.setattr(settings, "decime_prompt_pins", None)
    monkeypatch.setattr(settings, "decime_prompt_snapshot_dir", None)
    reset_prompt_cache()
    set_prompt_client_factory(None)
    yield
    reset_prompt_cache()
    set_prompt_client_factory(None)


def test_local_messages_keep_system_file_and_human_rules() -> None:
    request = TranslateToEsRequest(
        source_language="ru",
        source_text="Можно {оплатить} картой?",
        context=ReplyContext(channel="in_person", user_level="A2"),
    )
    human = _translate_user_content(request, reinforce_spanish=True)
    system, _human, identity = render_prompt(
        "translate_to_esuy",
        reinforce_spanish=True,
        level_is_a2=True,
        payload_json="{}",
    )
    assert system == read_system_markdown("translate_to_esuy")
    assert "CRITICAL RETRY:" in human
    assert "short simple A2-level wording" in human
    assert "natural wording at any complexity" not in human
    assert '"channel": "in_person"' in human
    assert "Можно {оплатить} картой?" in human
    assert identity.prompt_commit is None
    assert identity.prompt_source == "local"
    assert len(identity.prompt_sha256) == 64
    assert len(identity.schema_sha256) == 64


def test_locale_validate_is_not_a_production_prompt() -> None:
    assert "locale_validate_uy" not in PROMPT_IDS


def test_tracing_metadata_has_version_fields_and_not_user_text() -> None:
    _system, _human, identity = render_prompt(
        "understand_incoming",
        target_is_ru=False,
        payload_json='{"source_text": "Hola secreto"}',
    )
    metadata = identity.tracing_metadata(model="gpt-6-luna")
    config = build_run_config(
        operation="understand_incoming",
        provider="openai",
        model="gpt-6-luna",
        extra_metadata=metadata,
    )
    assert config is not None
    stored = config["metadata"]
    assert stored["prompt_id"] == "decime-understand-incoming"
    assert stored["prompt_sha256"] == identity.prompt_sha256
    assert stored["schema_sha256"] == identity.schema_sha256
    assert stored["model"] == "gpt-6-luna"
    assert stored["code_revision"]
    assert stored["prompt_source"] == "local"
    assert "prompt_commit" not in stored
    blob = json.dumps(stored)
    assert "Hola secreto" not in blob
    assert "sk-" not in blob


def test_langsmith_records_commit_not_environment_name(monkeypatch: pytest.MonkeyPatch) -> None:
    hub = FakeHub()
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    loaded = get_prompt("translate_to_esuy")
    assert loaded.prompt_commit == "a" * 64
    assert loaded.prompt_commit != "production"
    assert loaded.prompt_environment == "production"
    assert loaded.prompt_source == "langsmith"
    assert hub.calls[0] == ("resolve", "decime-translate-esuy:production")
    assert hub.calls[1] == ("pull", f"decime-translate-esuy:{'a' * 64}")
    again = get_prompt("translate_to_esuy")
    assert again is loaded
    assert hub.calls.count(("pull", f"decime-translate-esuy:{'a' * 64}")) == 1


def test_changing_resolved_commit_requires_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    hub = FakeHub()
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    first = get_prompt("extract_candidates")
    hub.commit = "b" * 64
    assert get_prompt("extract_candidates").prompt_commit == first.prompt_commit
    reset_prompt_cache()
    second = get_prompt("extract_candidates")
    assert second.prompt_commit == "b" * 64


def test_missing_variables_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    hub = FakeHub()
    hub.bad_template = True
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    with pytest.raises(PromptConfigError, match="missing template variables"):
        get_prompt("translate_to_esuy")


def test_environment_outage_does_not_use_another_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    template = build_local_template("translate_to_esuy")
    snapshot = LoadedPrompt(
        operation="translate_to_esuy",
        prompt_id="decime-translate-esuy",
        template=template,
        prompt_sha256=template_content_sha256(template),
        schema_sha256="0" * 64,
        prompt_source="langsmith",
        code_revision="unknown",
        prompt_commit="c" * 64,
    )
    monkeypatch.setattr(settings, "decime_prompt_snapshot_dir", str(tmp_path))
    write_snapshot(snapshot)
    hub = FakeHub()
    hub.fail_resolve = True
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    with pytest.raises(PromptConfigError, match="Could not resolve"):
        get_prompt("translate_to_esuy")


def test_pinned_commit_uses_matching_snapshot_when_hub_is_down(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    template = build_local_template("normalize_dictionary_row")
    commit = "d" * 64
    snapshot = LoadedPrompt(
        operation="normalize_dictionary_row",
        prompt_id="decime-normalize-dictionary",
        template=template,
        prompt_sha256=template_content_sha256(template),
        schema_sha256="0" * 64,
        prompt_source="langsmith",
        code_revision="unknown",
        prompt_commit=commit,
    )
    monkeypatch.setattr(settings, "decime_prompt_snapshot_dir", str(tmp_path))
    write_snapshot(snapshot)
    hub = FakeHub()
    hub.fail_resolve = True
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    monkeypatch.setattr(
        settings,
        "decime_prompt_pins",
        json.dumps({"decime-normalize-dictionary": commit}),
    )
    loaded = get_prompt("normalize_dictionary_row")
    assert loaded.prompt_source == "local_snapshot"
    assert loaded.prompt_commit == commit


def test_snapshot_for_a_different_commit_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    template = build_local_template("translate_to_esuy")
    snapshot = LoadedPrompt(
        operation="translate_to_esuy",
        prompt_id="decime-translate-esuy",
        template=template,
        prompt_sha256=template_content_sha256(template),
        schema_sha256="0" * 64,
        prompt_source="langsmith",
        code_revision="unknown",
        prompt_commit="e" * 64,
    )
    monkeypatch.setattr(settings, "decime_prompt_snapshot_dir", str(tmp_path))
    write_snapshot(snapshot)
    hub = FakeHub()
    hub.fail_pull = True
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    monkeypatch.setattr(
        settings,
        "decime_prompt_pins",
        json.dumps({"decime-translate-esuy": "f" * 64}),
    )
    with pytest.raises(PromptConfigError, match="will not substitute"):
        get_prompt("translate_to_esuy")


def test_corrupt_snapshot_and_hash_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "decime_prompt_snapshot_dir", str(tmp_path))
    path = tmp_path / "decime-translate-esuy.json"
    path.write_text("{", encoding="utf-8")
    hub = FakeHub()
    hub.fail_pull = True
    set_prompt_client_factory(lambda: hub)
    monkeypatch.setattr(settings, "decime_prompt_source", "langsmith")
    monkeypatch.setattr(
        settings,
        "decime_prompt_pins",
        json.dumps({"decime-translate-esuy": "a" * 64}),
    )
    with pytest.raises(PromptConfigError, match="not valid JSON"):
        get_prompt("translate_to_esuy")

    template = build_local_template("translate_to_esuy")
    write_snapshot(
        LoadedPrompt(
            operation="translate_to_esuy",
            prompt_id="decime-translate-esuy",
            template=template,
            prompt_sha256=template_content_sha256(template),
            schema_sha256="0" * 64,
            prompt_source="langsmith",
            code_revision="unknown",
            prompt_commit="a" * 64,
        )
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["content_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    reset_prompt_cache()
    with pytest.raises(PromptConfigError, match="hash mismatch"):
        get_prompt("translate_to_esuy")


def test_unknown_operation_and_local_mode_ignores_hub() -> None:
    set_prompt_client_factory(lambda: (_ for _ in ()).throw(AssertionError("hub called")))
    with pytest.raises(PromptConfigError, match="Unknown prompt"):
        get_prompt("locale_validate_uy")
    loaded = warm_prompt_cache()
    assert set(loaded) == set(PROMPT_IDS)


def test_tag_commit_uses_dash_owner_when_the_prompt_has_none() -> None:
    hub = FakeHub()

    def get_prompt(prompt_id: str) -> SimpleNamespace:
        return SimpleNamespace(full_name=prompt_id, owner=None)

    hub.get_prompt = get_prompt  # type: ignore[method-assign]
    tag_commit(hub, "decime-translate-esuy", "abc123def", "v1-0-0")
    assert hub.tags[0]["path"] == "/repos/-/decime-translate-esuy/tags"
    assert hub.tags[0]["commit_id"] == "80dd086c-3163-42e9-bae3-762a7ea3fe70"
    hub = FakeHub()
    tag_commit(hub, "decime-translate-esuy", "abc123def", "staging")
    assert hub.tags == [
        {
            "method": "POST",
            "path": "/repos/owner/decime-translate-esuy/tags",
            "tag_name": "staging",
            "commit_id": "80dd086c-3163-42e9-bae3-762a7ea3fe70",
        }
    ]


def test_regression_plan_does_not_claim_a_quality_change() -> None:
    plan = build_regression_plan(
        dataset="ru_esuy_judge_v1",
        model="gpt-6-luna",
        prompt_id="decime-translate-esuy",
        commit_a="a" * 64,
        commit_b="b" * 64,
    )
    assert plan["paid_execution"] is False
    assert plan["decision"] == "not_run"
    assert plan["changed"] == ["prompt_commit"]
    with pytest.raises(ValueError, match="must differ"):
        build_regression_plan(
            dataset="ru_esuy_judge_v1",
            model="gpt-6-luna",
            prompt_id="decime-translate-esuy",
            commit_a="same",
            commit_b="same",
        )


def test_scratch_database_guard_rejects_the_app_database() -> None:
    with pytest.raises(RuntimeError, match="test"):
        _assert_scratch_database("postgresql://decime:secret@postgres:5432/decime")
