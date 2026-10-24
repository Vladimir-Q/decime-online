"""Heuristics to catch compose replies that stayed in the source language."""

from __future__ import annotations

import re

_CYRILLIC = re.compile(r"[\u0400-\u04FF]")


def contains_cyrillic(text: str | None) -> bool:
    return bool(text and _CYRILLIC.search(text))


def spanish_reply_contaminated(*, source_language: str, source_text: str, reply_text: str) -> bool:
    """True when a to-Spanish reply still looks like Russian source language."""
    reply = (reply_text or "").strip()
    if not reply:
        return True
    source_is_ru = (source_language or "").lower().startswith("ru") or contains_cyrillic(source_text)
    return source_is_ru and contains_cyrillic(reply)
