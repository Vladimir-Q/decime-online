from typing import Literal

from pydantic import BaseModel, Field

AudioSourceType = Literal["user_voice", "whatsapp_audio"]
LanguageHint = Literal["auto", "ru", "en", "es"]
SynthesizeMode = Literal["training_reference", "reply"]
SynthesizeSpeed = Literal["slow", "normal"]


class TranscribeAudioResponse(BaseModel):
    audio_id: str
    transcript_id: str
    language: str
    transcript: str
    confidence_notes: list[str] = Field(default_factory=list)
    duration_ms: int | None = None


class SynthesizeAudioRequest(BaseModel):
    text: str = Field(min_length=1)
    locale: str = "es-UY-montevideo"
    mode: SynthesizeMode = "reply"
    speed: SynthesizeSpeed = "normal"


class SynthesizeAudioResponse(BaseModel):
    audio_id: str = ""
    audio_url: str = ""
    cached: bool = False
    status: Literal["pending", "ready", "error"] = "ready"
    job_id: str | None = None
    error: str | None = None


class SynthesizeJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "ready", "error"]
    audio_id: str = ""
    audio_url: str = ""
    cached: bool = False
    error: str | None = None
