"""OpenAI standard short-context list prices.

Source: https://developers.openai.com/api/docs/pricing
Captured: 2026-10-19. Rates are USD per 1M tokens, Standard tier, short context.

Long-context and Batch prices are not applied: Decime does not currently receive
a context-tier flag, and inventing one would under- or over-charge. Cached input
is priced only when the caller supplies a cached-token count. Historical rows are
not rewritten when this table changes; new calculations store ``pricing_version``.
"""

from __future__ import annotations

from dataclasses import dataclass

PRICING_VERSION = "openai-standard-short-2026-10-19"
PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing"

# name -> (input, cached_input or None, output)
_RATES: dict[str, tuple[float, float | None, float]] = {
    "gpt-4o-mini": (0.15, 0.075, 0.60),
    "gpt-4o-2024-05-13": (5.00, None, 15.00),
    "gpt-4o": (2.50, 1.25, 10.00),
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
    "gpt-4.1-nano": (0.10, 0.025, 0.40),
    "gpt-4.1": (2.00, 0.50, 8.00),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-6-luna": (0.10, 0.01, 0.50),
}


@dataclass(frozen=True)
class ModelRate:
    model_key: str
    input_usd_per_1m: float
    cached_input_usd_per_1m: float | None
    output_usd_per_1m: float
    pricing_version: str = PRICING_VERSION


def match_model_rate(model: str) -> ModelRate | None:
    """Longest published key that is the model id or a dated snapshot prefix."""
    key = (model or "").strip().lower()
    if not key:
        return None
    matches = [
        name
        for name in _RATES
        if key == name or key.startswith(f"{name}-")
    ]
    if not matches:
        return None
    name = max(matches, key=len)
    input_rate, cached_rate, output_rate = _RATES[name]
    return ModelRate(
        model_key=name,
        input_usd_per_1m=input_rate,
        cached_input_usd_per_1m=cached_rate,
        output_usd_per_1m=output_rate,
    )


def quote_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    cached_prompt_tokens: int | None = None,
) -> dict[str, object]:
    """Price actual token counts. Unknown models do not borrow another model's rate."""
    prompt = max(0, int(prompt_tokens or 0))
    completion = max(0, int(completion_tokens or 0))
    rate = match_model_rate(model)
    if rate is None:
        return {
            "price_status": "unknown_price",
            "pricing_version": PRICING_VERSION,
            "matched_model": None,
            "input_cost_usd": None,
            "output_cost_usd": None,
            "estimated_cost_usd": None,
        }

    cached = 0
    if cached_prompt_tokens is not None:
        cached = int(cached_prompt_tokens)
        if cached < 0 or cached > prompt or rate.cached_input_usd_per_1m is None:
            return {
                "price_status": "unknown_price",
                "pricing_version": PRICING_VERSION,
                "matched_model": rate.model_key,
                "input_cost_usd": None,
                "output_cost_usd": None,
                "estimated_cost_usd": None,
            }

    uncached = prompt - cached
    cached_rate = rate.cached_input_usd_per_1m or 0.0
    input_cost = (uncached * rate.input_usd_per_1m + cached * cached_rate) / 1_000_000
    output_cost = (completion * rate.output_usd_per_1m) / 1_000_000
    return {
        "price_status": "known",
        "pricing_version": PRICING_VERSION,
        "matched_model": rate.model_key,
        "input_cost_usd": round(input_cost, 8),
        "output_cost_usd": round(output_cost, 8),
        "estimated_cost_usd": round(input_cost + output_cost, 8),
    }
