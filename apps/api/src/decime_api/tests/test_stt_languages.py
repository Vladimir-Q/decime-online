from decime_api.services.ai.stt_languages import (
    infer_language_from_transcript,
    parse_language_hint,
    pick_allowed_language,
    resolve_explicit_language_hint,
)


def test_resolve_explicit_auto() -> None:
    assert resolve_explicit_language_hint("auto") is None
    assert resolve_explicit_language_hint("auto:ru,es") is None


def test_resolve_explicit_codes() -> None:
    assert resolve_explicit_language_hint("ru") == "ru"
    assert resolve_explicit_language_hint("en") == "en"
    assert resolve_explicit_language_hint("es-UY") == "es"


def test_parse_pair_hint() -> None:
    explicit, allowed = parse_language_hint("auto:ru,es")
    assert explicit is None
    assert allowed == frozenset({"ru", "es"})


def test_pick_allowed_from_probs() -> None:
    language, notes = pick_allowed_language(
        detected="pt",
        all_language_probs=[("pt", 0.7), ("es", 0.65), ("ru", 0.1)],
    )
    assert language == "es"
    assert notes


def test_pick_allowed_pair_excludes_en() -> None:
    language, notes = pick_allowed_language(
        detected="en",
        all_language_probs=[("en", 0.8), ("es", 0.5), ("ru", 0.4)],
        allowed=frozenset({"ru", "es"}),
    )
    assert language == "es"
    assert notes


def test_pick_allowed_detected_ok() -> None:
    language, notes = pick_allowed_language(detected="ru")
    assert language == "ru"
    assert not notes


def test_infer_from_transcript() -> None:
    assert (
        infer_language_from_transcript("Проверяю микрофон", frozenset({"ru", "es"})) == "ru"
    )
    assert (
        infer_language_from_transcript("Estoy probando", frozenset({"ru", "es"})) == "es"
    )
