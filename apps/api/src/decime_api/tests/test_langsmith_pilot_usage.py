"""LangSmith pilot upload maps Decime usage → usage_metadata (cost fields)."""

from __future__ import annotations

from decime_api.evals.langsmith_pilot import usage_metadata_for_langsmith
from decime_api.services.analytics.llm_usage import merge_usage_snapshots, usage_snapshot


def test_usage_snapshot_luna_rates() -> None:
    snap = usage_snapshot(
        model="gpt-6-luna",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    assert snap["input_cost_usd"] == 0.10
    assert snap["output_cost_usd"] == 0.50
    assert snap["estimated_cost_usd"] == 0.60


def test_merge_usage_snapshots_sums_retries() -> None:
    a = usage_snapshot(model="gpt-6-luna", prompt_tokens=100, completion_tokens=20)
    b = usage_snapshot(model="gpt-6-luna", prompt_tokens=50, completion_tokens=10)
    merged = merge_usage_snapshots(a, b)
    assert merged is not None
    assert merged["prompt_tokens"] == 150
    assert merged["completion_tokens"] == 30
    assert merged["estimated_cost_usd"] == round(a["estimated_cost_usd"] + b["estimated_cost_usd"], 8)


def test_usage_metadata_for_langsmith_includes_costs() -> None:
    snap = usage_snapshot(model="gpt-5.6-luna", prompt_tokens=2000, completion_tokens=500)
    meta = usage_metadata_for_langsmith(snap)
    assert meta["input_tokens"] == 2000
    assert meta["output_tokens"] == 500
    assert meta["total_tokens"] == 2500
    assert meta["input_cost"] == snap["input_cost_usd"]
    assert meta["output_cost"] == snap["output_cost_usd"]
    assert meta["total_cost"] == snap["estimated_cost_usd"]


def test_usage_metadata_empty_defaults_to_zeros() -> None:
    meta = usage_metadata_for_langsmith(None)
    assert meta == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
