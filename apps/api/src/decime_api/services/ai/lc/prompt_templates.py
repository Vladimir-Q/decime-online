"""Versioned ChatPromptTemplate builders for the four production text operations.

System text is the current markdown file, byte for byte.
Human instructions live in the template. User JSON is one unescaped variable
(``{{{payload_json}}}``) so braces in the payload are not template slots.

Mustache is used instead of Jinja2 because LangSmith ``pull_prompt`` reloads
templates through LangChain, and that loader refuses ``template_format='jinja2'``.

``locale_validate_uy.md`` is not built here: no production code loads it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

PROMPT_IDS: dict[str, str] = {
    "translate_to_esuy": "decime-translate-esuy",
    "understand_incoming": "decime-understand-incoming",
    "extract_candidates": "decime-extract-candidates",
    "normalize_dictionary_row": "decime-normalize-dictionary",
}

PROMPT_FILES: dict[str, str] = {
    "translate_to_esuy": "translate_to_esuy.md",
    "understand_incoming": "understand_incoming.md",
    "extract_candidates": "extract_training_items.md",
    "normalize_dictionary_row": "normalize_dictionary_item.md",
}

REQUIRED_VARIABLES: dict[str, frozenset[str]] = {
    "translate_to_esuy": frozenset({"reinforce_spanish", "level_is_a2", "payload_json"}),
    "understand_incoming": frozenset({"target_is_ru", "payload_json"}),
    "extract_candidates": frozenset({"payload_json"}),
    "normalize_dictionary_row": frozenset({"payload_json"}),
}

_TRANSLATE_HUMAN = (
    "{{#reinforce_spanish}}CRITICAL RETRY: your previous answer put Russian/English "
    "in recommended_reply. Rewrite recommended_reply in Uruguayan Spanish only.\n"
    "{{/reinforce_spanish}}"
    "Translate source_text into Uruguayan Spanish (es-UY) as what the USER will say "
    "or send. Preserve exact meaning. Do NOT answer or reply to source_text. "
    "Do NOT paraphrase in Russian or English.\n"
    "Apply the expert Uruguayan translator guidelines from the system prompt.\n"
    "{{#level_is_a2}}"
    "Put the single best Uruguayan Spanish translation in recommended_reply "
    "(Latin script, never Cyrillic). Use short simple A2-level wording; "
    "same facts as source_text."
    "{{/level_is_a2}}{{^level_is_a2}}"
    "Put the single best Uruguayan Spanish translation in recommended_reply "
    "(Latin script, never Cyrillic). Use natural wording at any complexity "
    "that fits the source."
    "{{/level_is_a2}}\n"
    "intent_summary_ru must list every idea from source_text.\n"
    "Generate a ReplyBundle JSON for this request:\n"
    "{{{payload_json}}}"
)

_UNDERSTAND_HUMAN = (
    "Translate source_text into "
    "{{#target_is_ru}}Russian (translation_ru only){{/target_is_ru}}"
    "{{^target_is_ru}}English (translation_en only){{/target_is_ru}}. "
    "Do not mix languages. Return UnderstandText JSON:\n"
    "{{{payload_json}}}"
)

_EXTRACT_HUMAN = "Extract training candidates as ExtractionBundle JSON:\n{{{payload_json}}}"

_NORMALIZE_HUMAN = "Normalize one dictionary row as TrainingCandidate JSON:\n{{{payload_json}}}"

_HUMAN_TEMPLATES: dict[str, str] = {
    "translate_to_esuy": _TRANSLATE_HUMAN,
    "understand_incoming": _UNDERSTAND_HUMAN,
    "extract_candidates": _EXTRACT_HUMAN,
    "normalize_dictionary_row": _NORMALIZE_HUMAN,
}


def read_system_markdown(operation: str) -> str:
    filename = PROMPT_FILES[operation]
    path = _PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def build_local_template(operation: str) -> ChatPromptTemplate:
    """Chat template whose rendered messages match the pre-migration builders."""
    if operation not in _HUMAN_TEMPLATES:
        raise KeyError(f"No versioned template for operation {operation!r}")
    system_text = read_system_markdown(operation)
    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_text),
            ("human", _HUMAN_TEMPLATES[operation]),
        ],
        template_format="mustache",
    )


def template_content_sha256(template: ChatPromptTemplate) -> str:
    """Hash of the template text, not of a filled user payload."""
    parts: list[dict[str, str]] = []
    for message in template.messages:
        prompt = getattr(message, "prompt", None)
        if prompt is not None and hasattr(prompt, "template"):
            parts.append(
                {
                    "kind": "template",
                    "role": message.__class__.__name__,
                    "text": prompt.template,
                }
            )
            continue
        content = getattr(message, "content", "")
        text = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
        parts.append(
            {
                "kind": "message",
                "role": getattr(message, "type", message.__class__.__name__),
                "text": text,
            }
        )
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def template_snapshot_manifest(template: ChatPromptTemplate) -> dict[str, Any]:
    """Plain message text. Rebuilt by Decime, not by LangChain's object loader."""
    messages: list[dict[str, str]] = []
    for message in template.messages:
        prompt = getattr(message, "prompt", None)
        if prompt is not None and hasattr(prompt, "template"):
            role = "human" if "Human" in message.__class__.__name__ else "system"
            messages.append({"role": role, "template": prompt.template})
            continue
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            raise TypeError("Snapshot messages must be text")
        messages.append({"role": getattr(message, "type", "system"), "content": content})
    return {"template_format": "mustache", "messages": messages}


def template_from_snapshot_manifest(manifest: dict[str, Any]) -> ChatPromptTemplate:
    if manifest.get("template_format") != "mustache":
        raise ValueError("Snapshot template_format must be mustache")
    items: list[Any] = []
    for message in manifest.get("messages") or []:
        if not isinstance(message, dict):
            raise TypeError("Snapshot message must be an object")
        role = message.get("role")
        if "content" in message and "template" not in message:
            if role != "system" or not isinstance(message["content"], str):
                raise ValueError("Only a static system message may use content")
            items.append(SystemMessage(content=message["content"]))
            continue
        if role not in {"system", "human"} or not isinstance(message.get("template"), str):
            raise ValueError("Snapshot template message is invalid")
        items.append((role, message["template"]))
    if len(items) != 2:
        raise ValueError("Snapshot must contain system and human messages")
    return ChatPromptTemplate.from_messages(items, template_format="mustache")


def schema_sha256(schema: dict[str, Any]) -> str:
    raw = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def missing_variables(template: ChatPromptTemplate, operation: str) -> list[str]:
    required = REQUIRED_VARIABLES[operation]
    present = set(template.input_variables)
    return sorted(required - present)


def render_template(template: ChatPromptTemplate, variables: dict[str, Any]) -> tuple[str, str]:
    messages = template.format_messages(**variables)
    if len(messages) != 2:
        raise ValueError(f"Expected system and human messages, got {len(messages)}")
    system = messages[0].content
    human = messages[1].content
    if not isinstance(system, str) or not isinstance(human, str):
        raise TypeError("Prompt messages must be text")
    return system, human
