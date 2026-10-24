"""STT input language constraints for Decime (ru / en / es only)."""

from __future__ import annotations

from collections.abc import Sequence

ALLOWED_STT_LANGUAGES: frozenset[str] = frozenset({"ru", "en", "es"})
DEFAULT_STT_LANGUAGE = "es"

# Default prompt when the full trio is allowed.
STT_INITIAL_PROMPT = (
    "The audio contains speech in Russian, English, or Spanish only. "
    "Treat those languages equally — do not prefer one over another. "
    "Transcribe exactly what is spoken. Use Cyrillic for Russian. "
    "Do not interpret speech as Polish, Ukrainian, or other languages."
)


def stt_prompt_for_languages(allowed: frozenset[str]) -> str:
    labels = {
        "ru": "Russian",
        "en": "English",
        "es": "Spanish",
    }
    names = [labels[code] for code in ("ru", "en", "es") if code in allowed]
    if not names:
        return STT_INITIAL_PROMPT
    joined = ", ".join(names[:-1]) + (f", or {names[-1]}" if len(names) > 1 else names[0])
    if len(names) == 1:
        joined = names[0]
    elif len(names) == 2:
        joined = f"{names[0]} or {names[1]}"
    return (
        f"The audio contains speech in {joined} only — treat them equally. "
        "Transcribe exactly what is spoken. Use Cyrillic for Russian when applicable. "
        "Do not interpret the speech as any other language "
        "(no Polish, Ukrainian, Portuguese, French, etc.)."
    )


def parse_language_hint(hint: str) -> tuple[str | None, frozenset[str]]:
    """Parse language_hint into (explicit_code|None, allowed_auto_set).

    Forms:
      auto          → (None, {ru,en,es})
      auto:ru,es    → (None, {ru,es})   # Live Chat Russian UI
      auto:en,es    → (None, {en,es})   # Live Chat English UI
      ru / en / es  → (code, {code})
    """
    normalized = (hint or "auto").strip().lower()
    if not normalized or normalized == "auto":
        return None, ALLOWED_STT_LANGUAGES

    if normalized.startswith("auto:"):
        parts = [p.strip().split("-")[0] for p in normalized[5:].split(",") if p.strip()]
        allowed = frozenset(p for p in parts if p in ALLOWED_STT_LANGUAGES)
        if not allowed:
            allowed = ALLOWED_STT_LANGUAGES
        return None, allowed

    base = normalized.split("-")[0]
    if base in ALLOWED_STT_LANGUAGES:
        return base, frozenset({base})
    return DEFAULT_STT_LANGUAGE, frozenset({DEFAULT_STT_LANGUAGE})


def resolve_explicit_language_hint(hint: str) -> str | None:
    """Return a fixed Whisper/OpenAI language code, or None for constrained auto-detect."""
    explicit, _allowed = parse_language_hint(hint)
    return explicit


def pick_allowed_language(
    *,
    detected: str | None = None,
    all_language_probs: Sequence[tuple[str, float]] | None = None,
    allowed: frozenset[str] | None = None,
) -> tuple[str, list[str]]:
    """Choose the best language from Whisper detection scores within `allowed`."""
    allowed_set = allowed or ALLOWED_STT_LANGUAGES
    default = "es" if "es" in allowed_set else next(iter(sorted(allowed_set)))
    notes: list[str] = []
    allowed_probs: list[tuple[str, float]] = []
    if all_language_probs:
        allowed_probs = [
            (lang, prob) for lang, prob in all_language_probs if lang in allowed_set
        ]

    if allowed_probs:
        chosen_lang, _ = max(allowed_probs, key=lambda item: item[1])
        if detected and detected not in allowed_set:
            notes.append(
                f"Detected '{detected}' outside {sorted(allowed_set)}; "
                f"transcribing as '{chosen_lang}'."
            )
        return chosen_lang, notes

    if detected in allowed_set:
        return detected, notes

    if detected:
        notes.append(
            f"Detected '{detected}' outside {sorted(allowed_set)}; "
            f"defaulting to '{default}'."
        )
    return default, notes


def infer_language_from_transcript(text: str, allowed: frozenset[str]) -> str:
    """Best-effort language tag from script when remote STT does not return one."""
    cyrillic = sum(1 for ch in text if "\u0400" <= ch <= "\u04ff")
    letters = sum(1 for ch in text if ch.isalpha())
    if letters and cyrillic / letters >= 0.5 and "ru" in allowed:
        return "ru"
    if "es" in allowed and "en" not in allowed:
        return "es"
    if "en" in allowed and "es" not in allowed:
        return "en"
    # Both en and es allowed, or ambiguous — prefer es for Decime defaults.
    if "es" in allowed:
        return "es"
    return next(iter(sorted(allowed))) if allowed else DEFAULT_STT_LANGUAGE
