import logging
from io import BytesIO

import httpx

from decime_api.services.ai.speech_provider import TranscriptResult
from decime_api.services.ai.stt_languages import (
    infer_language_from_transcript,
    parse_language_hint,
    stt_prompt_for_languages,
)

logger = logging.getLogger(__name__)


class OllamaSTTProvider:
    """Try OpenAI-compatible transcription on Ollama (if available).

    Standard Ollama does not implement /v1/audio/transcriptions.
    The karanchopda333/whisper tag in the Ollama library is text-only.
    Use STT_PROVIDER=faster_whisper for local Whisper ASR.
    """

    provider_name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        language_hint: str,
    ) -> TranscriptResult:
        url = f"{self.base_url}/v1/audio/transcriptions"
        explicit, allowed = parse_language_hint(language_hint)
        data: dict[str, str] = {
            "model": self.model_name,
            "prompt": stt_prompt_for_languages(allowed),
        }
        if explicit:
            data["language"] = explicit

        files = {"file": (filename or "audio.webm", BytesIO(audio_bytes), "application/octet-stream")}

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, data=data, files=files)

        if response.status_code == 404:
            raise RuntimeError(
                "Ollama does not expose /v1/audio/transcriptions. "
                "The karanchopda333/whisper tag in Ollama is text-only. "
                "Set STT_PROVIDER=faster_whisper in .env for local Whisper STT."
            )

        response.raise_for_status()
        payload = response.json()
        text = (payload.get("text") or payload.get("transcript") or "").strip()
        if not text:
            raise ValueError("Ollama STT returned empty transcript")

        language = explicit or infer_language_from_transcript(text, allowed)
        logger.info("transcribe provider=ollama model=%s language=%s", self.model_name, language)
        return TranscriptResult(language=language, transcript=text, confidence_notes=[])
