from decime_api.services.locale import normalize_locale_variant


def test_normalize_locale_variant_maps_shorthand() -> None:
    assert normalize_locale_variant("es-UY") == "es-UY-montevideo"
    assert normalize_locale_variant("ES-UY") == "es-UY-montevideo"
    assert normalize_locale_variant("es-UY-montevideo") == "es-UY-montevideo"
    assert normalize_locale_variant(None) == "es-UY-montevideo"
    assert normalize_locale_variant("") == "es-UY-montevideo"
