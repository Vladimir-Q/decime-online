import logging

import httpx

from decime_api.services.ai.speech_provider import SynthesisResult

logger = logging.getLogger(__name__)


class OrpheusTTSProvider:
    """Local Spanish TTS via Orpheus-FastAPI (OpenAI-compatible /v1/audio/speech).

    Requires Orpheus-FastAPI on ORPHEUS_TTS_BASE_URL (default :5005) with inference
    pointed at Ollama model sematre/orpheus:it_es.
    """

    provider_name = "orpheus"

    def __init__(self, base_url: str, model: str, voice: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.voice = voice

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
        selected_voice = voice or self.voice
        speed_value = 0.9 if speed == "slow" else 1.0
        url = f"{self.base_url}/v1/audio/speech"

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    url,
                    json={
                        "model": self.model_name,
                        "input": text,
                        "voice": selected_voice,
                        "response_format": "wav",
                        "speed": speed_value,
                    },
                )
        except httpx.ConnectError as error:
            logger.error("Orpheus TTS connect failed base_url=%s: %s", self.base_url, error)
            raise RuntimeError(
                "Voice synthesis is temporarily unavailable. Please try again shortly."
            ) from error
        except httpx.TimeoutException as error:
            logger.error("Orpheus TTS timeout base_url=%s: %s", self.base_url, error)
            raise RuntimeError(
                "Voice synthesis timed out. Please try again shortly."
            ) from error

        if response.status_code in (404, 502, 503):
            logger.error(
                "Orpheus TTS upstream HTTP %s base_url=%s",
                response.status_code,
                self.base_url,
            )
            raise RuntimeError(
                "Voice synthesis is temporarily unavailable. Please try again shortly."
            )

        response.raise_for_status()
        audio_bytes = response.content or b""
        # Empty WAV header is 44 bytes; Orpheus can return that after Ollama OOM.
        if len(audio_bytes) < 1024:
            logger.error(
                "Orpheus TTS empty audio bytes=%s base_url=%s",
                len(audio_bytes),
                self.base_url,
            )
            raise RuntimeError(
                "Voice synthesis failed. Please try again shortly."
            )
        logger.info(
            "synthesize provider=%s model=%s voice=%s bytes=%s",
            self.provider_name,
            self.model_name,
            selected_voice,
            len(audio_bytes),
        )
        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            extension="wav",
        )
