"""Shared parsing for training ExtractionBundle payloads from LLM JSON."""

from __future__ import annotations

from uuid import uuid4

from decime_api.schemas.training import (
    ExtractCandidatesRequest,
    ExtractionBundle,
    TrainingCandidate,
)
from decime_api.services.locale import normalize_locale_variant


def parse_extraction_bundle(
    raw: dict,
    request: ExtractCandidatesRequest,
) -> ExtractionBundle:
    skipped = raw.get("skipped_reasoning_summary")
    if isinstance(skipped, str):
        raw["skipped_reasoning_summary"] = [skipped] if skipped.strip() else []
    elif skipped is None:
        raw["skipped_reasoning_summary"] = []

    valid_status_hints = {"new", "learning", "known", "ignored", "duplicate_possible"}

    for candidate in raw.get("candidates", []):
        if not candidate.get("candidate_id"):
            candidate["candidate_id"] = str(uuid4())
        hint = candidate.get("status_hint")
        if not hint or hint not in valid_status_hints:
            candidate["status_hint"] = "new"
        grammar = candidate.get("grammar") or {}
        candidate["grammar"] = {k: v for k, v in grammar.items() if v is not None}
        for key in ("translations_ru", "translations_en", "governance"):
            value = candidate.get(key)
            if isinstance(value, str):
                candidate[key] = [value] if value.strip() else []
            elif value is None:
                candidate[key] = []

    bundle = ExtractionBundle.model_validate(raw)
    candidates: list[TrainingCandidate] = []
    for candidate in bundle.candidates:
        if candidate.item_type not in request.candidate_types:
            continue
        candidates.append(
            candidate.model_copy(
                update={
                    "candidate_id": candidate.candidate_id or str(uuid4()),
                    "locale_variant": normalize_locale_variant(
                        candidate.locale_variant or request.target_locale
                    ),
                    "example_es": candidate.example_es or request.spanish_text,
                }
            )
        )
    return bundle.model_copy(update={"candidates": candidates})
