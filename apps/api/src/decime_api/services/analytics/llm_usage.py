"""LLM token usage logging for admin cost dashboard."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from decime_api.db.postgres import postgres_cursor, use_postgres
from decime_api.services.analytics.llm_pricing import PRICING_VERSION, quote_cost

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    usage_id: str
    user_id: str | None
    operation: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    created_at: datetime
    price_status: str = "known"
    pricing_version: str | None = None
    usage_raw: dict[str, Any] | None = None


_memory_usage: list[UsageRecord] = []


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """Return USD, or None when the model has no published rate in the catalog."""
    quote = quote_cost(model, prompt_tokens, completion_tokens)
    cost = quote["estimated_cost_usd"]
    return None if cost is None else float(cost)


def usage_snapshot(
    *,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int | None = None,
    cached_prompt_tokens: int | None = None,
) -> dict[str, Any]:
    """Normalized per-call usage for eval reports / LangSmith cost upload.

    ``estimated_cost_usd`` is None when the model is not in the price catalog.
    Token counts are still returned so a later catalog can reprice the call.
    """
    prompt = max(0, int(prompt_tokens or 0))
    completion = max(0, int(completion_tokens or 0))
    total = int(total_tokens) if total_tokens is not None else prompt + completion
    quote = quote_cost(
        model,
        prompt,
        completion,
        cached_prompt_tokens=cached_prompt_tokens,
    )
    raw: dict[str, Any] = {
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
    }
    if total_tokens is not None:
        raw["total_tokens"] = int(total_tokens)
    if cached_prompt_tokens is not None:
        raw["cached_prompt_tokens"] = int(cached_prompt_tokens)
    return {
        "model": model,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "input_cost_usd": quote["input_cost_usd"],
        "output_cost_usd": quote["output_cost_usd"],
        "estimated_cost_usd": quote["estimated_cost_usd"],
        "price_status": quote["price_status"],
        "pricing_version": quote["pricing_version"],
        "usage_raw": raw,
    }


def merge_usage_snapshots(*parts: dict[str, Any] | None) -> dict[str, Any] | None:
    """Sum token/cost fields across retries; keep last non-empty model.

    A retry with an unknown price voids the summed dollar amount. Token counts
    are still added so the call can be repriced later.
    """
    merged: dict[str, Any] | None = None
    unknown = False
    cost_keys = ("input_cost_usd", "output_cost_usd", "estimated_cost_usd")
    token_keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    for part in parts:
        if not part:
            continue
        if part.get("price_status") == "unknown_price":
            unknown = True
        if merged is None:
            merged = dict(part)
            continue
        for key in token_keys:
            merged[key] = int(merged.get(key) or 0) + int(part.get(key) or 0)
        if not unknown:
            for key in cost_keys:
                merged[key] = float(merged.get(key) or 0) + float(part.get(key) or 0)
        if part.get("model"):
            merged["model"] = part["model"]
    if merged is None:
        return None
    for key in token_keys:
        merged[key] = int(merged.get(key) or 0)
    if unknown:
        merged["price_status"] = "unknown_price"
        for key in cost_keys:
            merged[key] = None
    else:
        merged["price_status"] = merged.get("price_status") or "known"
        for key in cost_keys:
            merged[key] = round(float(merged.get(key) or 0), 8)
    return merged


def reset_usage_store() -> None:
    _memory_usage.clear()


async def log_llm_usage(
    *,
    user_id: str | None,
    operation: str,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int | None = None,
) -> None:
    snap = usage_snapshot(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    priced = snap["estimated_cost_usd"]
    record = UsageRecord(
        usage_id=str(uuid4()),
        user_id=user_id,
        operation=operation,
        provider=provider,
        model=model,
        prompt_tokens=int(snap["prompt_tokens"]),
        completion_tokens=int(snap["completion_tokens"]),
        total_tokens=int(snap["total_tokens"]),
        estimated_cost_usd=0.0 if priced is None else float(priced),
        created_at=datetime.now(UTC),
        price_status=str(snap["price_status"]),
        pricing_version=str(snap["pricing_version"]) if snap.get("pricing_version") else None,
        usage_raw=snap.get("usage_raw") if isinstance(snap.get("usage_raw"), dict) else None,
    )

    if use_postgres():
        try:
            import json

            with postgres_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO llm_usage (
                        id, user_id, operation, provider, model,
                        prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd,
                        price_status, pricing_version, usage_raw
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        record.usage_id,
                        record.user_id,
                        record.operation,
                        record.provider,
                        record.model,
                        record.prompt_tokens,
                        record.completion_tokens,
                        record.total_tokens,
                        record.estimated_cost_usd,
                        record.price_status,
                        record.pricing_version,
                        json.dumps(record.usage_raw or {}),
                    ),
                )
        except Exception:
            logger.exception("Failed to write llm_usage %s", operation)
            _memory_usage.append(record)
    else:
        _memory_usage.append(record)


def usage_from_openai_response(response: Any) -> tuple[int, int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0, 0
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or (prompt + completion))
    return prompt, completion, total


def summarize_usage(*, days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(UTC).timestamp() - days * 86400
    rows = _load_usage_rows(days=days)
    filtered = [row for row in rows if row.created_at.timestamp() >= cutoff]

    by_operation: dict[str, dict[str, float | int]] = {}
    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    known_cost = 0.0
    legacy_cost = 0.0
    unknown_calls = 0

    for row in filtered:
        total_prompt += row.prompt_tokens
        total_completion += row.completion_tokens
        total_tokens += row.total_tokens
        bucket = by_operation.setdefault(
            row.operation,
            {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "unknown_price_calls": 0,
            },
        )
        bucket["calls"] = int(bucket["calls"]) + 1
        bucket["prompt_tokens"] = int(bucket["prompt_tokens"]) + row.prompt_tokens
        bucket["completion_tokens"] = int(bucket["completion_tokens"]) + row.completion_tokens
        bucket["total_tokens"] = int(bucket["total_tokens"]) + row.total_tokens
        if row.price_status == "unknown_price":
            unknown_calls += 1
            bucket["unknown_price_calls"] = int(bucket["unknown_price_calls"]) + 1
        elif row.price_status == "legacy_unverified":
            legacy_cost += row.estimated_cost_usd
        else:
            known_cost += row.estimated_cost_usd
            bucket["estimated_cost_usd"] = float(bucket["estimated_cost_usd"]) + row.estimated_cost_usd

    return {
        "days": days,
        "calls": len(filtered),
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(known_cost, 6),
        "known_cost_usd": round(known_cost, 6),
        "legacy_unverified_cost_usd": round(legacy_cost, 6),
        "unknown_price_calls": unknown_calls,
        "pricing_version": PRICING_VERSION,
        "by_operation": {
            key: {
                **value,
                "estimated_cost_usd": round(float(value["estimated_cost_usd"]), 6),
            }
            for key, value in sorted(by_operation.items())
        },
    }


def _load_usage_rows(*, days: int) -> list[UsageRecord]:
    if not use_postgres():
        return list(_memory_usage)

    try:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, operation, provider, model,
                       prompt_tokens, completion_tokens, total_tokens,
                       estimated_cost_usd, created_at,
                       price_status, pricing_version, usage_raw
                FROM llm_usage
                WHERE created_at >= NOW() - (%s || ' days')::interval
                ORDER BY created_at DESC
                """,
                (str(days),),
            )
            rows = cursor.fetchall()
        result: list[UsageRecord] = []
        for row in rows:
            created_at = row["created_at"]
            if not isinstance(created_at, datetime):
                created_at = datetime.fromisoformat(str(created_at))
            raw = row.get("usage_raw")
            if isinstance(raw, str):
                import json

                raw = json.loads(raw)
            result.append(
                UsageRecord(
                    usage_id=str(row["id"]),
                    user_id=str(row["user_id"]) if row.get("user_id") else None,
                    operation=row["operation"],
                    provider=row["provider"],
                    model=row["model"],
                    prompt_tokens=int(row["prompt_tokens"] or 0),
                    completion_tokens=int(row["completion_tokens"] or 0),
                    total_tokens=int(row["total_tokens"] or 0),
                    estimated_cost_usd=float(row["estimated_cost_usd"] or 0),
                    created_at=created_at,
                    price_status=str(row.get("price_status") or "legacy_unverified"),
                    pricing_version=row.get("pricing_version"),
                    usage_raw=raw if isinstance(raw, dict) else None,
                )
            )
        return result
    except Exception:
        logger.exception("Failed to load llm_usage summary")
        return list(_memory_usage)
