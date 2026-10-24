import wave
from io import BytesIO

from decime_api.services.ai.speech_provider import SynthesisResult, TranscriptResult


class FakeSTTProvider:
    provider_name = "fake"
    model_name = "fake-stt-v1"

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        language_hint: str,
    ) -> TranscriptResult:
        _ = audio_bytes
        if "factura" in filename.lower():
            return TranscriptResult(
                language="es",
                transcript="¿Me podés mandar la factura?",
                confidence_notes=["fake_stt_response"],
            )
        return TranscriptResult(
            language=language_hint if language_hint != "auto" else "es",
            transcript="Hola, quería consultar si se puede pagar con tarjeta.",
            confidence_notes=["fake_stt_response"],
        )


class FakeTTSProvider:
    provider_name = "fake"
    model_name = "fake-tts-v1"

    async def synthesize(
        self,
        text: str,
        *,
        locale: str,
        mode: str,
        speed: str,
        voice: str,
    ) -> SynthesisResult:
        _ = text, locale, mode, speed, voice
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            frames = b"\x00\x00" * 22050
            wav_file.writeframes(frames)
        return SynthesisResult(
            audio_bytes=buffer.getvalue(),
            mime_type="audio/wav",
            extension="wav",
        )
