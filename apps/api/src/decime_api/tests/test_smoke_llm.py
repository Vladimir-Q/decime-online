"""Live LLM smoke tests — excluded from default pytest / CI.

Enable explicitly:

  DECIME_LLM_SMOKE=1 OPENAI_API_KEY=... pytest -m smoke_llm

Optional:

  LLM_ORCHESTRATOR=langchain  # exercise LangChain path
"""

from __future__ import annotations

import os

import pytest

from decime_api.schemas.compose import ReplyContext, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest
from decime_api.services.ai.reply_language import contains_cyrillic

pytestmark = pytest.mark.smoke_llm


def _smoke_enabled() -> bool:
    return os.environ.get("DECIME_LLM_SMOKE", "").strip() in {"1", "true", "yes"}


def _openai_ready() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


requires_openai_smoke = pytest.mark.skipif(
    not (_smoke_enabled() and _openai_ready()),
    reason="Set DECIME_LLM_SMOKE=1 and OPENAI_API_KEY to run live OpenAI smoke",
)


@requires_openai_smoke
@pytest.mark.asyncio
async def test_openai_compose_smoke_spanish_reply() -> None:
    from decime_api.config import settings
    from decime_api.services.ai.openai_llm import OpenAILLMProvider

    provider = OpenAILLMProvider(
        api_key=settings.openai_api_key or os.environ["OPENAI_API_KEY"],
        model=settings.openai_text_model,
    )
    bundle = await provider.translate_to_esuy(
        TranslateToEsRequest(
            source_language="ru",
            source_text="Можно оплатить картой?",
            context=ReplyContext(channel="whatsapp_text"),
        )
    )
    assert bundle.recommended_reply.strip()
    assert not contains_cyrillic(bundle.recommended_reply)
    assert "tarjeta" in bundle.recommended_reply.lower() or "pagar" in bundle.recommended_reply.lower()


@requires_openai_smoke
@pytest.mark.asyncio
async def test_openai_understand_smoke_russian() -> None:
    from decime_api.config import settings
    from decime_api.services.ai.openai_llm import OpenAILLMProvider

    provider = OpenAILLMProvider(
        api_key=settings.openai_api_key or os.environ["OPENAI_API_KEY"],
        model=settings.openai_text_model,
    )
    result = await provider.understand_incoming(
        UnderstandTextRequest(
            source_text="¿Se puede pagar con tarjeta?",
            target_language="ru",
        )
    )
    assert result.translation_ru and result.translation_ru.strip()
    assert contains_cyrillic(result.translation_ru)
