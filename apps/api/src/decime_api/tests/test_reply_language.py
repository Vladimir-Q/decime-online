from decime_api.services.ai.reply_language import (
    contains_cyrillic,
    spanish_reply_contaminated,
)


def test_contains_cyrillic() -> None:
    assert contains_cyrillic("тестируем")
    assert not contains_cyrillic("Estamos probando")


def test_spanish_reply_contaminated_when_russian_returned() -> None:
    assert spanish_reply_contaminated(
        source_language="ru",
        source_text="тестируем микрофон",
        reply_text="Мы тестируем микрофон.",
    )


def test_spanish_reply_ok() -> None:
    assert not spanish_reply_contaminated(
        source_language="ru",
        source_text="тестируем микрофон",
        reply_text="Estamos probando el micrófono.",
    )
