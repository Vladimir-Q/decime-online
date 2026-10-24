import asyncio
import logging
import tempfile
from pathlib import Path

from decime_api.services.ai.speech_provider import TranscriptResult
from decime_api.services.ai.stt_languages import (
    parse_language_hint,
    pick_allowed_language,
    stt_prompt_for_languages,
)

logger = logging.getLogger(__name__)

_model_cache: dict[str, object] = {}


def clear_whisper_model_cache() -> None:
    _model_cache.clear()


def whisper_model_is_warm(model_size: str, *, cpu_threads: int = 0, num_workers: int = 1) -> bool:
    cache_key = f"{model_size}:t{max(0, cpu_threads)}:w{max(1, num_workers)}"
    return cache_key in _model_cache


class FasterWhisperSTTProvider:
    provider_name = "faster_whisper"

    def __init__(
        self,
        model_size: str,
        *,
        cpu_threads: int = 0,
        num_workers: int = 1,
    ) -> None:
        self.model_name = model_size
        self.cpu_threads = max(0, cpu_threads)
        self.num_workers = max(1, num_workers)

    def _cache_key(self) -> str:
        return f"{self.model_name}:t{self.cpu_threads}:w{self.num_workers}"

    def _get_model(self):
        cache_key = self._cache_key()
        if cache_key not in _model_cache:
            from faster_whisper import WhisperModel

            kwargs: dict = {
                "device": "cpu",
                "compute_type": "int8",
                "num_workers": self.num_workers,
            }
            if self.cpu_threads > 0:
                kwargs["cpu_threads"] = self.cpu_threads
            _model_cache[cache_key] = WhisperModel(self.model_name, **kwargs)
        return _model_cache[cache_key]

    def is_warm(self) -> bool:
        return self._cache_key() in _model_cache

    async def warm(self) -> None:
        await asyncio.to_thread(self._get_model)
        logger.info("whisper warm model=%s", self.model_name)

    def unload(self) -> None:
        _model_cache.pop(self._cache_key(), None)
        logger.info("whisper unload model=%s", self.model_name)

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        language_hint: str,
    ) -> TranscriptResult:
        _ = filename
        suffix = Path(filename).suffix if filename and "." in filename else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            return await asyncio.to_thread(
                self._transcribe_file,
                tmp_path,
                language_hint,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _transcribe_file(self, path: str, language_hint: str) -> TranscriptResult:
        from faster_whisper.audio import decode_audio

        model = self._get_model()
        explicit, allowed = parse_language_hint(language_hint)
        notes: list[str] = []
        prompt = stt_prompt_for_languages(allowed)

        if explicit:
            language = explicit
        else:
            audio = decode_audio(path)
            detected, _, all_probs = model.detect_language(audio, vad_filter=True)
            language, notes = pick_allowed_language(
                detected=detected,
                all_language_probs=all_probs,
                allowed=allowed,
            )

        segments, info = model.transcribe(
            path,
            language=language,
            initial_prompt=prompt,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if info.language not in (None, language) and info.language:
            notes.append(
                f"Model run used '{language}'; raw detection was '{info.language}'."
            )
        logger.info(
            "transcribe provider=faster_whisper model=%s language=%s allowed=%s",
            self.model_name,
            language,
            sorted(allowed),
        )
        return TranscriptResult(
            language=language,
            transcript=text,
            confidence_notes=notes,
        )
