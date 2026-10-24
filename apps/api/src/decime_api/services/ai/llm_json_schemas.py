"""JSON schemas for structured LLM outputs (OpenAI + Ollama)."""


def understand_text_json_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "original_text",
            "translation_ru",
            "translation_en",
            "tone_notes_ru",
            "uncertain_parts",
            "detected_locale",
        ],
        "properties": {
            "original_text": {"type": "string"},
            "translation_ru": {"type": ["string", "null"]},
            "translation_en": {"type": ["string", "null"]},
            "tone_notes_ru": {"type": "array", "items": {"type": "string"}},
            "uncertain_parts": {"type": "array", "items": {"type": "string"}},
            "detected_locale": {"type": ["string", "null"]},
        },
    }


def reply_bundle_json_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "target_locale",
            "dialect_stamp",
            "source_language",
            "intent_summary_ru",
            "intent_summary_en",
            "recommended_reply",
            "warnings",
            "can_add_to_training",
        ],
        "properties": {
            "target_locale": {"type": "string"},
            "dialect_stamp": {"type": "string"},
            "source_language": {"type": "string"},
            "intent_summary_ru": {"type": "string"},
            "intent_summary_en": {"type": ["string", "null"]},
            "recommended_reply": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "can_add_to_training": {"type": "boolean"},
        },
    }


def judge_translate_pilot_json_schema() -> dict:
    """Structured Outputs schema for Experiment 2 LLM-as-a-Judge (RU→es-UY)."""
    score = {"type": "integer", "minimum": 1, "maximum": 5}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "semantic_fidelity",
            "uy_naturalness",
            "style_preservation",
            "no_additions_omissions",
            "critical_error",
            "rationale",
            "error_category",
        ],
        "properties": {
            "semantic_fidelity": score,
            "uy_naturalness": score,
            "style_preservation": score,
            "no_additions_omissions": score,
            "critical_error": {"type": "boolean"},
            "rationale": {"type": "string"},
            "error_category": {
                "type": "string",
                "enum": [
                    "none",
                    "meaning_drift",
                    "omission",
                    "addition",
                    "register_mismatch",
                    "unnatural_spanish",
                    "wrong_locale",
                    "wrong_language",
                    "other",
                ],
            },
        },
    }


def _grammar_json_schema() -> dict:
    nullable = {"type": ["string", "null"]}
    nullable_bool = {"type": ["boolean", "null"]}
    nullable_int = {"type": ["integer", "null"]}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "pronoun": nullable,
            "person": nullable_int,
            "number": nullable,
            "tense": nullable,
            "mood": nullable,
            "voseo": nullable_bool,
            "article": nullable,
            "gender": nullable,
        },
        "required": [
            "pronoun",
            "person",
            "number",
            "tense",
            "mood",
            "voseo",
            "article",
            "gender",
        ],
    }


def _candidate_json_schema(*, include_idioms: bool = False) -> dict:
    item_types = ["noun", "adjective", "verb_form", "verb_infinitive"]
    if include_idioms:
        item_types.extend(["idiom", "expression"])
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "candidate_id",
            "item_type",
            "surface_text",
            "display_text",
            "lemma",
            "locale_variant",
            "translations_ru",
            "translations_en",
            "context_translation_ru",
            "context_translation_en",
            "grammar",
            "governance",
            "example_es",
            "example_ru",
            "example_en",
            "status_hint",
            "canonical_key",
        ],
        "properties": {
            "candidate_id": {"type": ["string", "null"]},
            "item_type": {
                "type": "string",
                "enum": item_types,
            },
            "surface_text": {"type": "string"},
            "display_text": {"type": "string"},
            "lemma": {"type": ["string", "null"]},
            "locale_variant": {"type": "string"},
            "translations_ru": {"type": "array", "items": {"type": "string"}},
            "translations_en": {"type": "array", "items": {"type": "string"}},
            "context_translation_ru": {"type": ["string", "null"]},
            "context_translation_en": {"type": ["string", "null"]},
            "grammar": _grammar_json_schema(),
            "governance": {"type": "array", "items": {"type": "string"}},
            "example_es": {"type": ["string", "null"]},
            "example_ru": {"type": ["string", "null"]},
            "example_en": {"type": ["string", "null"]},
            "status_hint": {
                "type": "string",
                "enum": ["new", "learning", "known", "ignored", "duplicate_possible"],
            },
            "canonical_key": {"type": ["string", "null"]},
        },
    }


def extraction_bundle_json_schema() -> dict:
    # Multi-item extract stays on lexical types only (no idiom/expression regression).
    candidate_schema = _candidate_json_schema(include_idioms=False)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "target_locale",
            "source_language",
            "spanish_text",
            "candidates",
            "skipped_reasoning_summary",
        ],
        "properties": {
            "target_locale": {"type": "string"},
            "source_language": {"type": "string"},
            "spanish_text": {"type": "string"},
            "candidates": {"type": "array", "items": candidate_schema},
            "skipped_reasoning_summary": {"type": "array", "items": {"type": "string"}},
        },
    }


def normalize_dictionary_item_json_schema() -> dict:
    return _candidate_json_schema(include_idioms=True)
