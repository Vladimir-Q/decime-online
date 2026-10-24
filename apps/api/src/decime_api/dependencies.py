from decime_api.config import settings
from decime_api.db.history import get_history_repository
from decime_api.services.ai.fake_llm import FakeLLMProvider
from decime_api.services.ai.fake_speech import FakeSTTProvider, FakeTTSProvider
from decime_api.services.ai.fake_training_extractor import FakeTrainingExtractor
from decime_api.services.ai.faster_whisper_stt import FasterWhisperSTTProvider
from decime_api.services.ai.llm_provider import LLMProvider
from decime_api.services.ai.ollama_stt import OllamaSTTProvider
from decime_api.services.ai.openai_llm import OpenAILLMProvider
from decime_api.services.ai.openai_speech import OpenAISTTProvider, OpenAITTSProvider
from decime_api.services.ai.openai_training_extractor import OpenAITrainingExtractor
from decime_api.services.ai.orpheus_tts import OrpheusTTSProvider
from decime_api.services.ai.speech_provider import STTProvider, TTSProvider
from decime_api.services.ai.training_extractor import TrainingExtractor
from decime_api.services.storage.audio_storage import LocalAudioStorage

_audio_storage: LocalAudioStorage | None = None


def _effective_tts_provider() -> str:
    if settings.tts_provider:
        return settings.tts_provider
    if settings.speech_provider:
        return settings.speech_provider
    return "fake"


def get_training_extractor() -> TrainingExtractor:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAITrainingExtractor(
            api_key=settings.openai_api_key,
            model=settings.openai_text_model,
            base_url=settings.openai_text_base_url,
        )
    return FakeTrainingExtractor()


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_text_model,
            base_url=settings.openai_text_base_url,
        )
    return FakeLLMProvider()


def get_stt_provider() -> STTProvider:
    provider = settings.stt_provider
    if provider == "openai":
        # Cloud OpenAI needs a real key; edge Whisper only needs a custom base URL.
        if settings.openai_stt_base_url:
            return OpenAISTTProvider(
                api_key=settings.openai_api_key or "sk-local",
                model=settings.openai_stt_model,
                base_url=settings.openai_stt_base_url,
            )
        if settings.openai_api_key:
            return OpenAISTTProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_stt_model,
            )
    if provider == "ollama":
        return OllamaSTTProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_stt_model,
        )
    if provider in ("faster_whisper", "local"):
        return FasterWhisperSTTProvider(
            model_size=settings.whisper_model_size,
            cpu_threads=settings.whisper_cpu_threads,
            num_workers=settings.whisper_num_workers,
        )
    return FakeSTTProvider()


def get_tts_provider() -> TTSProvider:
    provider = _effective_tts_provider()
    if provider == "openai" and settings.openai_api_key:
        return OpenAITTSProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
        )
    if provider == "orpheus":
        return OrpheusTTSProvider(
            base_url=settings.orpheus_tts_base_url,
            model=settings.orpheus_tts_model,
            voice=settings.orpheus_tts_voice,
        )
    return FakeTTSProvider()


def get_audio_storage() -> LocalAudioStorage:
    global _audio_storage
    if _audio_storage is None:
        _audio_storage = LocalAudioStorage(settings.audio_storage_path)
    return _audio_storage


def reset_audio_storage() -> None:
    global _audio_storage
    _audio_storage = None


__all__ = [
    "get_audio_storage",
    "get_history_repository",
    "get_llm_provider",
    "get_stt_provider",
    "get_training_extractor",
    "get_tts_provider",
    "reset_audio_storage",
]
