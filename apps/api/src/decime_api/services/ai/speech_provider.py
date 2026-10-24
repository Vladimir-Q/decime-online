from dataclasses import dataclass
from typing import Protocol


@dataclass
class TranscriptResult:
    language: str
    transcript: str
    confidence_notes: list[str]


@dataclass
class SynthesisResult:
    audio_bytes: bytes
    mime_type: str
    extension: str


class STTProvider(Protocol):
    provider_name: str
    model_name: str

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        language_hint: str,
    ) -> TranscriptResult: ...


class TTSProvider(Protocol):
    provider_name: str
    model_name: str

    async def synthesize(
        self,
        text: str,
        *,
        locale: str,
        mode: str,
        speed: str,
        voice: str,
    ) -> SynthesisResult: ...
