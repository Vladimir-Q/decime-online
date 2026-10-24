from typing import Literal

from pydantic import BaseModel, Field

from decime_api.schemas.limits import MAX_TRANSLATION_SOURCE_CHARS

TargetExplanationLanguage = Literal["ru", "en"]
IncomingChannel = Literal["whatsapp_text", "whatsapp_voice", "in_person", "support_chat", "email"]


class UnderstandTextRequest(BaseModel):
    source_text: str = Field(min_length=1, max_length=MAX_TRANSLATION_SOURCE_CHARS)
    source_language: str = "es"
    target_language: TargetExplanationLanguage = "ru"
    locale_variant: str = "es-UY-montevideo"
    channel: IncomingChannel = "whatsapp_text"


class UnderstandTextResponse(BaseModel):
    original_text: str
    translation_ru: str | None = None
    translation_en: str | None = None
    tone_notes_ru: list[str] = Field(default_factory=list)
    uncertain_parts: list[str] = Field(default_factory=list)
    detected_locale: str | None = None
