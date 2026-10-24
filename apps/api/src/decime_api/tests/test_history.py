import pytest

from decime_api.auth.user_scope import LOCAL_ANONYMOUS_USER_ID
from decime_api.schemas.compose import TranslateToEsRequest
from decime_api.services.ai.fake_llm import FakeLLMProvider
from decime_api.services.compose.dialect_stamp import build_dialect_stamp
from decime_api.services.compose.reply_composer import MemoryHistoryRepository, translate_to_esuy


@pytest.mark.asyncio
async def test_memory_history_repository_roundtrip() -> None:
    repo = MemoryHistoryRepository()
    llm = FakeLLMProvider()
    request = TranslateToEsRequest(source_text="Я хочу уточнить, можно ли оплатить картой.")
    response = await translate_to_esuy(LOCAL_ANONYMOUS_USER_ID, request, llm, repo)

    history = await repo.list_history(LOCAL_ANONYMOUS_USER_ID)
    assert history.total == 1
    assert history.items[0].request_id == response.request_id
    assert "tarjeta" in history.items[0].recommended_reply


def test_build_dialect_stamp() -> None:
    request = TranslateToEsRequest(source_text="test")
    stamp = build_dialect_stamp(request.context)
    assert "Montevideo" in stamp
    assert "WhatsApp" in stamp
