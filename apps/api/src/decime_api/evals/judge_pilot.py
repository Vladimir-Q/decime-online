"""Experiment 2 LLM-as-a-Judge (RU → es-UY) — Structured Outputs via LangChain.

Does not name candidate models. Rubric language and rationale are English.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from decime_api.services.ai.llm_json_schemas import judge_translate_pilot_json_schema
from decime_api.services.analytics.llm_usage import usage_snapshot

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator for Decime UY, a Montevideo-oriented Spanish learning app.

Score ONE Spanish translation of a Russian source. Do NOT invent a better translation.
Do NOT mention or guess which model produced the candidate.
Write rationale in English only.

## Rubric (each criterion integer 1–5)

### semantic_fidelity (PRIMARY)
5 = All facts, constraints, hedges, and intent preserved
4 = Tiny wording drift; meaning intact
3 = Noticeable soft omission or mild shift
2 = Important meaning lost or changed
1 = Wrong meaning / wrong language / empty

### uy_naturalness
5 = Natural spoken/written Uruguayan Spanish (es-UY / Montevideo feel: vos, local phrasing OK)
4 = Natural LatAm Spanish; slight non-UY flavor only
3 = Understandable but stiff / textbook / Spain-leaning
2 = Awkward or unnatural Spanish
1 = Broken Spanish or not Spanish

### style_preservation
5 = Register, politeness, emotion, and soft irony match the source
4 = Close register; minor tone flattening
3 = Tone partly flattened or mismatched
2 = Wrong register (too rude / too formal / wrong emotion)
1 = Style destroyed or contradictory

### no_additions_omissions
5 = No invented facts; no dropped constraints
4 = Harmless filler only
3 = Small omission or mild padding
2 = Material addition or omission
1 = Fabrication or severe omission

## critical_error
true if wrong language, empty/gibberish, inverted meaning, or unsafe/harmful rewrite; else false.

## error_category
Pick the single best label: none | meaning_drift | omission | addition | register_mismatch | unnatural_spanish | wrong_locale | wrong_language | other.
Use none when all scores are >= 4 and critical_error is false.

## Output
Return only the structured object matching the schema.
"""


def _clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(5, score))


def normalize_judge_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Validate/clamp judge fields for reports and LangSmith feedback."""
    allowed = {
        "none",
        "meaning_drift",
        "omission",
        "addition",
        "register_mismatch",
        "unnatural_spanish",
        "wrong_locale",
        "wrong_language",
        "other",
    }
    category = str(data.get("error_category") or "other").strip().lower()
    if category not in allowed:
        category = "other"
    return {
        "semantic_fidelity": _clamp_score(data.get("semantic_fidelity")),
        "uy_naturalness": _clamp_score(data.get("uy_naturalness")),
        "style_preservation": _clamp_score(data.get("style_preservation")),
        "no_additions_omissions": _clamp_score(data.get("no_additions_omissions")),
        "critical_error": bool(data.get("critical_error")),
        "rationale": str(data.get("rationale") or "").strip(),
        "error_category": category,
    }


async def llm_judge_translate_pilot(
    *,
    source_text: str,
    recommended_reply: str,
    context: dict[str, Any] | None,
    api_key: str,
    model: str = "gpt-5-mini",
    base_url: str | None = None,
) -> dict[str, Any]:
    """Judge one Spanish candidate. Returns scores + usage; never includes model role names."""
    from decime_api.services.ai.lc.structured_chat import ainvoke_structured

    user_payload = {
        "source_language": "ru",
        "source_text": source_text,
        "candidate_spanish": recommended_reply,
        "request_context": context or {},
    }
    user_content = (
        "Evaluate this translation candidate for Decime UY.\n"
        + json.dumps(user_payload, ensure_ascii=False, indent=2)
    )

    temperature: float | None = 0.0
    try:
        result = await ainvoke_structured(
            operation="llm_judge_translate",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            user_content=user_content,
            schema=judge_translate_pilot_json_schema(),
            schema_title="judge_translate_pilot",
            provider="openai",
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
    except Exception as exc:
        # Some models reject temperature=0; retry with API default.
        if temperature is not None and "temperature" in str(exc).lower():
            logger.warning("judge retry without temperature after: %s", exc)
            result = await ainvoke_structured(
                operation="llm_judge_translate",
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_content=user_content,
                schema=judge_translate_pilot_json_schema(),
                schema_title="judge_translate_pilot",
                provider="openai",
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=None,
            )
        else:
            raise

    scores = normalize_judge_payload(dict(result.get("data") or {}))
    usage = usage_snapshot(
        model=model,
        prompt_tokens=result.get("prompt_tokens") or 0,
        completion_tokens=result.get("completion_tokens") or 0,
        total_tokens=result.get("total_tokens"),
    )
    return {
        **scores,
        "judge_model": model,
        "usage": usage,
        "latency_ms": result.get("latency_ms"),
    }
