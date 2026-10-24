"""Optional LLM-as-a-Judge (paid). Disabled unless explicitly requested.

Legacy single-score helper for ``run_llm_eval.py --judge`` smoke only.

Pilot Experiment 2 (4 criteria + Structured Outputs) lives in
``decime_api.evals.judge_pilot`` / ``scripts/eval_stage5_judge.py``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = """You are an evaluator for Uruguayan Spanish (es-UY / Montevideo) learning apps.
Score ONLY the Spanish user-facing reply (or translation) against the source intent.
Return strict JSON: {"score": <1-5 integer>, "pass": <bool>, "rationale": "<one short sentence>"}.
Rubric:
5 = faithful meaning, natural es-UY, appropriate register/style, no extras
4 = minor style issues only
3 = mostly ok but awkward / mild omission
2 = meaning drift or unwanted additions
1 = wrong language, empty, or unsafe/wrong meaning
pass=true when score >= 4.
"""


async def llm_judge_translate(
    *,
    source_text: str,
    recommended_reply: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """Judge a Spanish translation. Requires OpenAI API key."""
    from openai import AsyncOpenAI

    user = {
        "source_text": source_text,
        "recommended_reply": recommended_reply,
    }
    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM},
            {
                "role": "user",
                "content": "Evaluate this Decime reply:\n" + json.dumps(user, ensure_ascii=False),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("judge returned non-JSON: %s", raw[:200])
        return {"score": 0, "pass": False, "rationale": "judge_parse_error", "raw": raw[:200]}
    score = int(data.get("score") or 0)
    return {
        "score": score,
        "pass": bool(data.get("pass", score >= 4)),
        "rationale": str(data.get("rationale") or ""),
    }
