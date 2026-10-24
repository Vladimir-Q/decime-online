"""Deterministic evaluators — no LLM judge, no API cost."""

from __future__ import annotations

import re
from typing import Any

from decime_api.services.ai.reply_language import contains_cyrillic

_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_LATIN = re.compile(r"[A-Za-zÀ-ÿ]")


def _has_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def evaluate_translate_case(bundle: Any, expect: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    reply = (getattr(bundle, "recommended_reply", None) or "").strip()

    checks.append(_check("non_empty_reply", bool(reply), detail=f"len={len(reply)}"))
    min_chars = int(expect.get("min_reply_chars") or 0)
    if min_chars:
        checks.append(
            _check(
                "min_reply_chars",
                len(reply) >= min_chars,
                detail=f"{len(reply)} >= {min_chars}",
            )
        )
    if expect.get("forbid_cyrillic_in_reply"):
        checks.append(
            _check(
                "forbid_cyrillic_in_reply",
                not contains_cyrillic(reply),
                detail="reply must be Latin-script Spanish",
            )
        )
    needles = expect.get("must_contain_any") or []
    if needles:
        checks.append(
            _check(
                "must_contain_any",
                _has_any(reply, needles),
                detail=f"need one of {needles}",
            )
        )
    for field in expect.get("required_fields") or []:
        value = getattr(bundle, field, None)
        checks.append(_check(f"required:{field}", bool(value), detail=str(type(value))))
    return checks


def evaluate_understand_case(result: Any, expect: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    field = expect.get("translation_field") or "translation_ru"
    text = (getattr(result, field, None) or "").strip()
    checks.append(_check("non_empty_translation", bool(text), detail=f"field={field}"))
    min_chars = int(expect.get("min_chars") or 0)
    if min_chars:
        checks.append(_check("min_chars", len(text) >= min_chars, detail=f"{len(text)}"))
    if expect.get("forbid_cyrillic"):
        checks.append(_check("forbid_cyrillic", not _CYRILLIC.search(text), detail=field))
    if expect.get("forbid_latin_letters"):
        checks.append(_check("forbid_latin_letters", not _LATIN.search(text), detail=field))
    needles = expect.get("must_contain_any") or []
    if needles:
        checks.append(_check("must_contain_any", _has_any(text, needles), detail=str(needles)))
    return checks


def evaluate_extract_case(bundle: Any, expect: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    candidates = list(getattr(bundle, "candidates", []) or [])
    min_c = int(expect.get("min_candidates") or 0)
    checks.append(_check("min_candidates", len(candidates) >= min_c, detail=f"n={len(candidates)}"))
    types_any = expect.get("required_item_types_any") or []
    if types_any:
        have = {c.item_type for c in candidates}
        checks.append(
            _check(
                "required_item_types_any",
                any(t in have for t in types_any),
                detail=f"have={sorted(have)}",
            )
        )
    surfaces = expect.get("surface_must_contain_any") or []
    if surfaces:
        blob = " ".join(c.surface_text for c in candidates).lower()
        checks.append(
            _check(
                "surface_must_contain_any",
                any(s.lower() in blob for s in surfaces),
                detail=str(surfaces),
            )
        )
    return checks


def _check(name: str, passed: bool, *, detail: str = "") -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for c in checks if c["passed"])
    return {
        "passed": passed == len(checks) and len(checks) > 0,
        "passed_checks": passed,
        "total_checks": len(checks),
        "failed": [c["name"] for c in checks if not c["passed"]],
    }
