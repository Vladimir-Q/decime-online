"""Shared parsing for single-card dictionary normalization."""

from __future__ import annotations

from uuid import uuid4

from decime_api.schemas.training import TrainingCandidate
from decime_api.services.locale import normalize_locale_variant
from decime_api.services.training.display_text import apply_article_to_display


def split_russian_translations(russian: str | None) -> list[str] | None:
    if russian is None:
        return None
    text = russian.strip()
    if not text:
        return None
    parts = [part.strip() for part in text.split(";") if part.strip()]
    return parts or None


def parse_normalized_candidate(
    raw: dict,
    *,
    spanish: str,
    russian: str | None,
    target_locale: str = "es-UY-montevideo",
) -> TrainingCandidate:
    data = dict(raw)
    if not data.get("candidate_id"):
        data["candidate_id"] = str(uuid4())
    hint = data.get("status_hint")
    if hint not in {"new", "learning", "known", "ignored", "duplicate_possible"}:
        data["status_hint"] = "new"
    grammar = data.get("grammar") or {}
    if isinstance(grammar, dict):
        data["grammar"] = {k: v for k, v in grammar.items() if v is not None}
    else:
        data["grammar"] = {}
    for key in ("translations_ru", "translations_en", "governance"):
        value = data.get(key)
        if isinstance(value, str):
            data[key] = [value] if value.strip() else []
        elif value is None:
            data[key] = []

    supplied = split_russian_translations(russian)
    if supplied is not None:
        data["translations_ru"] = supplied

    if not (data.get("display_text") or "").strip():
        data["display_text"] = spanish.strip()
    if not (data.get("surface_text") or "").strip():
        data["surface_text"] = data["display_text"]

    display, surface, grammar = apply_article_to_display(
        display_text=data["display_text"],
        surface_text=data.get("surface_text"),
        grammar=data.get("grammar"),
    )
    data["display_text"] = display
    data["surface_text"] = surface
    data["grammar"] = grammar
    data["locale_variant"] = normalize_locale_variant(
        data.get("locale_variant") or target_locale
    )
    data["example_es"] = data.get("example_es") or spanish.strip()
    data["canonical_key"] = None

    return TrainingCandidate.model_validate(data)
