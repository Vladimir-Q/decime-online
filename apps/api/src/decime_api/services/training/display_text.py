"""Helpers for consistent dictionary display_text (articles without doubling)."""

from __future__ import annotations

import re

_ARTICLE_RE = re.compile(
    r"^(el|la|los|las|un|una|unos|unas)\b[\s.]*",
    re.IGNORECASE,
)


def strip_leading_article(text: str) -> str:
    return _ARTICLE_RE.sub("", (text or "").strip()).strip()


def text_starts_with_article(text: str, article: str) -> bool:
    cleaned = (text or "").strip()
    art = (article or "").strip()
    if not cleaned or not art:
        return False
    pattern = re.compile(rf"^{re.escape(art)}\b", re.IGNORECASE)
    return bool(pattern.search(cleaned))


def apply_article_to_display(
    *,
    display_text: str,
    surface_text: str | None = None,
    grammar: dict | None = None,
) -> tuple[str, str, dict]:
    """Ensure noun display/surface include grammar.article once, without doubling."""
    grammar = dict(grammar or {})
    display = (display_text or "").strip()
    surface = (surface_text or display).strip()
    article = (grammar.get("article") or "").strip() if isinstance(grammar.get("article"), str) else ""

    if not article:
        return display, surface, grammar

    if text_starts_with_article(display, article):
        # Keep grammar.article; display already has it.
        return display, surface if surface else display, grammar

    # display may already start with a *different* article — replace leading article.
    if _ARTICLE_RE.match(display):
        rest = strip_leading_article(display)
        display = f"{article} {rest}".strip() if rest else article
    else:
        display = f"{article} {display}".strip()

    if not surface or not text_starts_with_article(surface, article):
        if _ARTICLE_RE.match(surface):
            rest = strip_leading_article(surface)
            surface = f"{article} {rest}".strip() if rest else article
        else:
            surface = display

    return display, surface, grammar
