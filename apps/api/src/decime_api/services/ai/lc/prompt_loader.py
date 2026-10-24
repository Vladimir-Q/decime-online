"""Load Decime prompt markdown files (no LangChain dependency)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# lc/ → ai/ → services/ → decime_api/
_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Return UTF-8 text for ``prompts/{name}`` (e.g. ``translate_to_esuy.md``)."""
    path = _PROMPTS_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def translate_to_esuy_system_prompt() -> str:
    from decime_api.services.ai.lc.prompt_provider import system_prompt_text

    return system_prompt_text("translate_to_esuy")


def understand_incoming_system_prompt() -> str:
    from decime_api.services.ai.lc.prompt_provider import system_prompt_text

    return system_prompt_text("understand_incoming")


def extract_training_system_prompt() -> str:
    from decime_api.services.ai.lc.prompt_provider import system_prompt_text

    return system_prompt_text("extract_candidates")


def normalize_dictionary_system_prompt() -> str:
    from decime_api.services.ai.lc.prompt_provider import system_prompt_text

    return system_prompt_text("normalize_dictionary_row")
