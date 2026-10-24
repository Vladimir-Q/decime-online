"""Locale helpers for Decime UY."""

from decime_api.config import settings

DEFAULT_LOCALE_VARIANT = settings.app_locale_default


def normalize_locale_variant(value: str | None) -> str:
    """Map LLM shorthand locales to the canonical DB locale id."""
    if not value or not value.strip():
        return DEFAULT_LOCALE_VARIANT

    normalized = value.strip()
    lowered = normalized.lower()

    if lowered in {"es-uy", "es_uy", "uruguay", "es-uy-montevideo"}:
        return DEFAULT_LOCALE_VARIANT

    if lowered.startswith("es-uy"):
        return DEFAULT_LOCALE_VARIANT

    return normalized
