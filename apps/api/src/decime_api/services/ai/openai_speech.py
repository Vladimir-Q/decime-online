import logging

from decime_api.services.ai.speech_provider import SynthesisResult, TranscriptResult
from decime_api.services.ai.stt_languages import (
    infer_language_from_transcript,
    parse_language_hint,
    stt_prompt_for_languages,
)

logger = logging.getLogger(__name__)

TTS_INSTRUCTIONS = (
    "Speak in natural Uruguayan Spanish from Montevideo. "
    "Use a clear, neutral, not exaggerated Rioplatense tone. "
    "Moderate speed. Suitable for a learner to imitate."
)


class OpenAISTTProvider:
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, *, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url.rstrip("/") if base_url else None
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            kwargs: dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        language_hint: str,
    ) -> TranscriptResult:
        from io import BytesIO

        client = self._get_client()
        file_obj = BytesIO(audio_bytes)
        file_obj.name = filename or "audio.webm"

        explicit, allowed = parse_language_hint(language_hint)
        kwargs: dict = {
            "model": self.model_name,
            "file": file_obj,
            "prompt": stt_prompt_for_languages(allowed),
        }
        if explicit:
            kwargs["language"] = explicit

        response = await client.audio.transcriptions.create(**kwargs)
        text = (getattr(response, "text", None) or str(response)).strip()
        language = explicit or infer_language_from_transcript(text, allowed)
        logger.info(
            "transcribe provider=%s model=%s language=%s allowed=%s",
            self.provider_name,
            self.model_name,
            language,
            sorted(allowed),
        )
        return TranscriptResult(language=language, transcript=text, confidence_notes=[])


class OpenAITTSProvider:
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self.api_key = api_key
        self.model_name = model
        self.voice = voice
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def synthesize(
        self,
        text: str,
        *,
        locale: str,
        mode: str,
        speed: str,
        voice: str,
    ) -> SynthesisResult:
        _ = locale, mode
        client = self._get_client()
        selected_voice = voice or self.voice
        speed_value = 0.9 if speed == "slow" else 1.0

        response = await client.audio.speech.create(
            model=self.model_name,
            voice=selected_voice,
            input=text,
            instructions=TTS_INSTRUCTIONS,
            speed=speed_value,
        )
        audio_bytes = await response.aread()
        logger.info("synthesize provider=%s model=%s voice=%s", self.provider_name, self.model_name, selected_voice)
        return SynthesisResult(audio_bytes=audio_bytes, mime_type="audio/mpeg", extension="mp3")
