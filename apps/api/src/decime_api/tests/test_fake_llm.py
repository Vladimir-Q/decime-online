import pytest

from decime_api.schemas.compose import ReplyContext, TranslateToEsRequest
from decime_api.services.ai.fake_llm import FakeLLMProvider


@pytest.mark.asyncio
async def test_fake_llm_card_payment_ru() -> None:
    provider = FakeLLMProvider()
    request = TranslateToEsRequest(
        source_text="Я хочу уточнить, можно ли оплатить картой.",
        context=ReplyContext(channel="whatsapp_text"),
    )
    bundle = await provider.translate_to_esuy(request)
    assert "tarjeta" in bundle.recommended_reply
    assert bundle.source_language == "ru"
    assert "🇺🇾" in bundle.dialect_stamp


@pytest.mark.asyncio
async def test_fake_llm_translate_send_now() -> None:
    provider = FakeLLMProvider()
    request = TranslateToEsRequest(
        source_text="Да, сейчас отправлю.",
    )
    bundle = await provider.translate_to_esuy(request)
    assert "mando" in bundle.recommended_reply.lower()
