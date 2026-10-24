"""Stage 2: LangChain OpenAI adapter unit tests (no live OpenAI calls)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from decime_api.schemas.compose import ReplyContext, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest
from decime_api.services.ai.lc.callbacks import tokens_from_ai_message, tokens_from_structured_raw
from decime_api.services.ai.lc.openai_backend import schema_with_title
from decime_api.services.ai.lc.types import StructuredInvokeResult
from decime_api.services.ai.openai_llm import OpenAILLMProvider, _translate_user_content


def test_schema_with_title_sets_top_level_title() -> None:
    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    titled = schema_with_title(schema, "reply_bundle")
    assert titled["title"] == "reply_bundle"
    assert schema.get("title") is None


def test_tokens_from_ai_message() -> None:
    message = SimpleNamespace(usage_metadata={"input_tokens": 11, "output_tokens": 7, "total_tokens": 18})
    assert tokens_from_ai_message(message) == (11, 7, 18)
    assert tokens_from_structured_raw({"raw": message}) == (11, 7, 18)


def test_translate_user_content_includes_payload() -> None:
    request = TranslateToEsRequest(
        source_language="ru",
        source_text="Можно оплатить картой?",
        context=ReplyContext(channel="whatsapp_text", user_level=None),
    )
    text = _translate_user_content(request, reinforce_spanish=False)
    assert "Можно оплатить картой?" in text
    assert "incoming_text" not in text
    assert "output_options" not in text
    assert "Translate source_text" in text


@pytest.mark.asyncio
async def test_translate_langchain_path_mocked() -> None:
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini")
    fake_result: StructuredInvokeResult = {
        "data": {
            "target_locale": "es-UY-montevideo",
            "dialect_stamp": "es-UY · Montevideo",
            "source_language": "ru",
            "intent_summary_ru": "Спросить про карту",
            "intent_summary_en": "Ask about card",
            "recommended_reply": "¿Se puede pagar con tarjeta?",
            "warnings": [],
            "can_add_to_training": True,
        },
        "provider": "openai",
        "model": "gpt-4o-mini",
        "operation": "translate_to_esuy",
        "latency_ms": 12,
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
    }
    with (
        patch(
            "decime_api.services.ai.lc.structured_chat.ainvoke_structured",
            new=AsyncMock(return_value=fake_result),
        ) as mocked,
        patch("decime_api.services.analytics.llm_usage.log_llm_usage", new=AsyncMock()) as logged,
    ):
        bundle = await provider.translate_to_esuy(
            TranslateToEsRequest(
                source_language="ru",
                source_text="Можно оплатить картой?",
            )
        )

    assert "tarjeta" in bundle.recommended_reply
    mocked.assert_awaited()
    logged.assert_awaited()
    call_kwargs = mocked.await_args.kwargs
    assert call_kwargs["operation"] == "translate_to_esuy"
    assert call_kwargs["schema_title"] == "reply_bundle"
    assert call_kwargs["api_key"] == "sk-test"


@pytest.mark.asyncio
async def test_understand_incoming_langchain_path_mocked() -> None:
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini")
    fake_result: StructuredInvokeResult = {
        "data": {
            "original_text": "ignored",
            "translation_ru": "Можешь прийти завтра?",
            "translation_en": None,
            "tone_notes_ru": [],
            "uncertain_parts": [],
            "detected_locale": "es-UY",
        },
        "provider": "openai",
        "model": "gpt-4o-mini",
        "operation": "understand_incoming",
        "latency_ms": 8,
        "prompt_tokens": 40,
        "completion_tokens": 10,
        "total_tokens": 50,
    }
    with (
        patch(
            "decime_api.services.ai.lc.structured_chat.ainvoke_structured",
            new=AsyncMock(return_value=fake_result),
        ),
        patch("decime_api.services.analytics.llm_usage.log_llm_usage", new=AsyncMock()),
    ):
        result = await provider.understand_incoming(
            UnderstandTextRequest(
                source_text="¿Podés venir mañana?",
                target_language="ru",
            )
        )

    assert result.original_text == "¿Podés venir mañana?"
    assert result.translation_ru == "Можешь прийти завтра?"
