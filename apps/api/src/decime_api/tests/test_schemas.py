import pytest
from pydantic import ValidationError

from decime_api.schemas.audio import SynthesizeAudioRequest, TranscribeAudioResponse
from decime_api.schemas.compose import ReplyBundle, ReplyContext, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest
from decime_api.schemas.limits import MAX_TRANSLATION_SOURCE_CHARS
from decime_api.schemas.training import ExtractionBundle, TrainingCandidate


def test_reply_context_defaults() -> None:
    context = ReplyContext()
    assert context.target_locale == "es-UY-montevideo"
    assert context.channel == "whatsapp_text"
    assert context.user_level is None


def test_translate_request_requires_source_text() -> None:
    with pytest.raises(ValidationError):
        TranslateToEsRequest(source_text="")


def test_translate_and_understand_reject_over_char_limit() -> None:
    too_long = "a" * (MAX_TRANSLATION_SOURCE_CHARS + 1)
    with pytest.raises(ValidationError):
        TranslateToEsRequest(source_text=too_long)
    with pytest.raises(ValidationError):
        UnderstandTextRequest(source_text=too_long)
    ok = "b" * MAX_TRANSLATION_SOURCE_CHARS
    assert TranslateToEsRequest(source_text=ok).source_text == ok
    assert UnderstandTextRequest(source_text=ok).source_text == ok


def test_reply_bundle_validation() -> None:
    bundle = ReplyBundle(
        target_locale="es-UY-montevideo",
        dialect_stamp="🇺🇾 Uruguay · Montevideo · WhatsApp · neutral amable · A2-friendly",
        source_language="ru",
        intent_summary_ru="Тест",
        recommended_reply="Hola",
    )
    assert bundle.can_add_to_training is True


def test_training_candidate_validation() -> None:
    candidate = TrainingCandidate(
        candidate_id="c1",
        item_type="verb_form",
        surface_text="podés",
        display_text="vos podés",
        translations_ru=["ты можешь"],
        translations_en=["you can"],
    )
    assert candidate.lemma is None


def test_extraction_bundle_validation() -> None:
    bundle = ExtractionBundle(
        source_language="es",
        spanish_text="¿Me podés mandar la factura?",
        candidates=[],
    )
    assert bundle.target_locale == "es-UY-montevideo"


def test_audio_schemas() -> None:
    synth = SynthesizeAudioRequest(text="Hola")
    transcript = TranscribeAudioResponse(
        audio_id="a1",
        transcript_id="t1",
        language="es",
        transcript="Hola",
    )
    assert synth.locale == "es-UY-montevideo"
    assert transcript.transcript == "Hola"
