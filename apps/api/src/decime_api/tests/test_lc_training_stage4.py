"""LangChain training extract/normalize (mocked, no live LLM)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from decime_api.schemas.training import ExtractCandidatesRequest
from decime_api.services.ai.openai_training_extractor import OpenAITrainingExtractor


def _extraction_payload() -> dict:
    return {
        "target_locale": "es-UY-montevideo",
        "source_language": "es",
        "spanish_text": "¿Se puede pagar con tarjeta?",
        "skipped_reasoning_summary": [],
        "candidates": [
            {
                "candidate_id": None,
                "item_type": "noun",
                "surface_text": "tarjeta",
                "display_text": "la tarjeta",
                "lemma": "tarjeta",
                "locale_variant": "es-UY-montevideo",
                "translations_ru": ["карта"],
                "translations_en": ["card"],
                "context_translation_ru": None,
                "context_translation_en": None,
                "grammar": {"article": "la", "gender": "f", "number": "singular"},
                "governance": [],
                "example_es": "¿Se puede pagar con tarjeta?",
                "example_ru": None,
                "example_en": None,
                "status_hint": "new",
                "canonical_key": None,
            }
        ],
    }


@pytest.mark.asyncio
async def test_openai_extract_langchain_path() -> None:
    extractor = OpenAITrainingExtractor(api_key="sk-test", model="gpt-4o-mini")
    with patch(
        "decime_api.services.ai.lc.structured_chat.ainvoke_structured",
        new=AsyncMock(
            return_value={
                "data": _extraction_payload(),
                "provider": "openai",
                "model": "gpt-4o-mini",
                "operation": "extract_candidates",
                "latency_ms": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        ),
    ) as mocked:
        bundle = await extractor.extract_candidates(
            ExtractCandidatesRequest(
                source_type="generated_reply",
                source_language="es",
                spanish_text="¿Se puede pagar con tarjeta?",
            )
        )

    assert len(bundle.candidates) == 1
    assert bundle.candidates[0].surface_text == "tarjeta"
    assert bundle.candidates[0].candidate_id
    mocked.assert_awaited()
    assert mocked.await_args.kwargs["schema_title"] == "extraction_bundle"


@pytest.mark.asyncio
async def test_openai_normalize_langchain_path() -> None:
    extractor = OpenAITrainingExtractor(api_key="sk-test", model="gpt-4o-mini")
    raw_candidate = {
        "candidate_id": None,
        "item_type": "noun",
        "surface_text": "tarjeta",
        "display_text": "tarjeta",
        "lemma": "tarjeta",
        "locale_variant": "es-UY",
        "translations_ru": ["ignored"],
        "translations_en": ["card"],
        "context_translation_ru": None,
        "context_translation_en": None,
        "grammar": {"article": "la", "gender": "f"},
        "governance": [],
        "example_es": None,
        "example_ru": None,
        "example_en": None,
        "status_hint": "new",
        "canonical_key": None,
    }
    with patch(
        "decime_api.services.ai.lc.structured_chat.ainvoke_structured",
        new=AsyncMock(
            return_value={
                "data": raw_candidate,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "operation": "normalize_dictionary_row",
                "latency_ms": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        ),
    ) as mocked:
        candidate = await extractor.normalize_dictionary_row(
            spanish="tarjeta",
            russian="банковская карта",
        )

    assert candidate.translations_ru == ["банковская карта"]
    assert candidate.surface_text
    mocked.assert_awaited()
    assert mocked.await_args.kwargs["provider"] == "openai"
    assert mocked.await_args.kwargs["schema_title"] == "normalize_dictionary_item"


@pytest.mark.asyncio
async def test_extract_filters_disallowed_item_types() -> None:
    payload = _extraction_payload()
    payload["candidates"].append(
        {
            **payload["candidates"][0],
            "item_type": "idiom",
            "surface_text": "dale",
            "display_text": "dale",
            "lemma": "dale",
        }
    )
    extractor = OpenAITrainingExtractor(api_key="sk-test", model="gpt-4o-mini")
    with patch(
        "decime_api.services.ai.lc.structured_chat.ainvoke_structured",
        new=AsyncMock(
            return_value={
                "data": payload,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "operation": "extract_candidates",
                "latency_ms": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        ),
    ):
        bundle = await extractor.extract_candidates(
            ExtractCandidatesRequest(
                source_type="generated_reply",
                source_language="es",
                spanish_text="¿Se puede pagar con tarjeta?",
            )
        )

    assert [c.surface_text for c in bundle.candidates] == ["tarjeta"]
