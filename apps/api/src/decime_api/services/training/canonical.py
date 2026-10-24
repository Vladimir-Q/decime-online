import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_phrase(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "").strip().lower())


def build_canonical_key(
    *,
    item_type: str,
    surface_text: str,
    lemma: str | None,
    grammar: dict | None,
) -> str:
    base = normalize_phrase(lemma or surface_text)
    grammar = grammar or {}

    if item_type == "noun":
        number = grammar.get("number", "singular")
        return f"noun:{base}:{number}"

    if item_type == "adjective":
        gender = grammar.get("gender", "")
        number = grammar.get("number", "singular")
        return f"adj:{base}:{gender}:{number}"

    if item_type == "verb_form":
        person = grammar.get("person", "")
        tense = grammar.get("tense", "")
        mood = grammar.get("mood", "")
        return f"verb_form:{base}:{person}:{tense}:{mood}"

    if item_type == "verb_infinitive":
        return f"verb_inf:{base}"

    if item_type == "idiom":
        return f"idiom:{base}"

    if item_type == "expression":
        return f"expression:{base}"

    return f"{item_type}:{base}"
