"""LLM price catalog: known models, unknown models, and zero usage."""

from __future__ import annotations

from decime_api.services.analytics.llm_pricing import PRICING_VERSION, quote_cost
from decime_api.services.analytics.llm_usage import (
    log_llm_usage,
    reset_usage_store,
    summarize_usage,
    usage_snapshot,
)


def test_known_models_use_short_context_standard_rates() -> None:
    luna = quote_cost("gpt-6-luna", 1_000_000, 1_000_000)
    assert luna["price_status"] == "known"
    assert luna["estimated_cost_usd"] == 0.60
    assert luna["pricing_version"] == PRICING_VERSION

    mini = quote_cost("gpt-4o-mini-2024-07-18", 1_000_000, 0)
    assert mini["matched_model"] == "gpt-4o-mini"
    assert mini["input_cost_usd"] == 0.15

    full = quote_cost("gpt-4o", 1_000_000, 0)
    assert full["matched_model"] == "gpt-4o"
    assert full["input_cost_usd"] == 2.50


def test_unknown_model_is_not_priced_as_gpt_4o_mini() -> None:
    quote = quote_cost("totally-unknown-model", 1_000_000, 1_000_000)
    assert quote["price_status"] == "unknown_price"
    assert quote["estimated_cost_usd"] is None
    assert quote["input_cost_usd"] is None


def test_zero_usage_known_model_is_zero_dollars() -> None:
    quote = quote_cost("gpt-5-mini", 0, 0)
    assert quote["price_status"] == "known"
    assert quote["estimated_cost_usd"] == 0.0


def test_snapshot_keeps_raw_counts_for_unknown_model() -> None:
    snap = usage_snapshot(
        model="not-a-real-model",
        prompt_tokens=12,
        completion_tokens=3,
        total_tokens=15,
    )
    assert snap["price_status"] == "unknown_price"
    assert snap["estimated_cost_usd"] is None
    assert snap["usage_raw"] == {
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
    }
    assert snap["prompt_tokens"] == 12
    assert snap["completion_tokens"] == 3


def test_cached_tokens_use_cached_rate_when_provided() -> None:
    quote = quote_cost("gpt-6-luna", 1_000_000, 0, cached_prompt_tokens=1_000_000)
    assert quote["price_status"] == "known"
    assert quote["input_cost_usd"] == 0.01


async def test_dashboard_separates_known_and_unknown_cost() -> None:
    reset_usage_store()
    await log_llm_usage(
        user_id=None,
        operation="translate_to_esuy",
        provider="openai",
        model="gpt-6-luna",
        prompt_tokens=1_000_000,
        completion_tokens=0,
    )
    await log_llm_usage(
        user_id=None,
        operation="translate_to_esuy",
        provider="openai",
        model="not-a-real-model",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    summary = summarize_usage(days=1)
    assert summary["known_cost_usd"] == 0.1
    assert summary["unknown_price_calls"] == 1
    assert summary["estimated_cost_usd"] == 0.1
    assert summary["legacy_unverified_cost_usd"] == 0.0
    reset_usage_store()
