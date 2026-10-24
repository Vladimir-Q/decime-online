from typing import Protocol

from decime_api.schemas.compose import ReplyBundle, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest, UnderstandTextResponse


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    async def translate_to_esuy(self, request: TranslateToEsRequest) -> ReplyBundle: ...

    async def understand_incoming(self, request: UnderstandTextRequest) -> UnderstandTextResponse: ...
