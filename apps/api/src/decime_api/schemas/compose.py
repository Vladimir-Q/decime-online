from typing import Literal

from pydantic import BaseModel, Field

from decime_api.schemas.limits import MAX_TRANSLATION_SOURCE_CHARS

Channel = Literal["whatsapp_text", "in_person"]
UserLevel = Literal["A1", "A2", "B1", "B2"]
SourceLanguage = Literal["auto", "ru", "en", "es"]


class ReplyContext(BaseModel):
    target_locale: str = "es-UY-montevideo"
    channel: Channel = "whatsapp_text"
    user_level: UserLevel | None = None


class TranslateToEsRequest(BaseModel):
    """RU/EN (or auto) → es-UY translation only."""

    source_language: SourceLanguage = "auto"
    source_text: str = Field(min_length=1, max_length=MAX_TRANSLATION_SOURCE_CHARS)
    context: ReplyContext = Field(default_factory=ReplyContext)


class ReplyBundle(BaseModel):
    target_locale: str
    dialect_stamp: str
    source_language: str
    intent_summary_ru: str
    intent_summary_en: str | None = None
    recommended_reply: str
    warnings: list[str] = Field(default_factory=list)
    can_add_to_training: bool = True


class TranslateToEsResponse(ReplyBundle):
    request_id: str
