"""User translation quality ratings (−1 / 0 / 1)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from decime_api.db.postgres import postgres_cursor, use_postgres

logger = logging.getLogger(__name__)

RatingFeature = Literal["quick_reply", "live_chat"]
RatingValue = Literal[-1, 0, 1]


@dataclass
class RatingRecord:
    rating_id: str
    user_id: str | None
    feature: str
    rating: int
    source_text: str | None
    result_text: str | None
    direction: str | None
    created_at: datetime


_memory_ratings: list[RatingRecord] = []


def reset_ratings_store() -> None:
    _memory_ratings.clear()


async def save_translation_rating(
    *,
    user_id: str | None,
    feature: RatingFeature,
    rating: RatingValue,
    source_text: str | None = None,
    result_text: str | None = None,
    direction: str | None = None,
) -> RatingRecord:
    record = RatingRecord(
        rating_id=str(uuid4()),
        user_id=user_id,
        feature=feature,
        rating=int(rating),
        source_text=source_text,
        result_text=result_text,
        direction=direction,
        created_at=datetime.now(UTC),
    )

    if use_postgres():
        try:
            with postgres_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO translation_ratings (
                        id, user_id, feature, rating, source_text, result_text, direction
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.rating_id,
                        record.user_id,
                        record.feature,
                        record.rating,
                        record.source_text,
                        record.result_text,
                        record.direction,
                    ),
                )
            return record
        except Exception:
            logger.exception("Failed to write translation_rating")

    _memory_ratings.append(record)
    return record


def summarize_ratings(*, days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(UTC).timestamp() - days * 86400
    rows = _load_rating_rows(days=days)
    filtered = [row for row in rows if row.created_at.timestamp() >= cutoff]

    counts = {"good": 0, "mixed": 0, "bad": 0}
    by_feature: dict[str, dict[str, int]] = {}
    score_sum = 0

    for row in filtered:
        score_sum += row.rating
        if row.rating == 1:
            counts["good"] += 1
            key = "good"
        elif row.rating == 0:
            counts["mixed"] += 1
            key = "mixed"
        else:
            counts["bad"] += 1
            key = "bad"
        bucket = by_feature.setdefault(row.feature, {"good": 0, "mixed": 0, "bad": 0, "total": 0})
        bucket[key] += 1
        bucket["total"] += 1

    total = len(filtered)
    return {
        "days": days,
        "total": total,
        "counts": counts,
        "average_score": round(score_sum / total, 3) if total else 0.0,
        "by_feature": by_feature,
    }


def _load_rating_rows(*, days: int) -> list[RatingRecord]:
    if not use_postgres():
        return list(_memory_ratings)

    try:
        with postgres_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, feature, rating, source_text, result_text, direction, created_at
                FROM translation_ratings
                WHERE created_at >= NOW() - (%s || ' days')::interval
                ORDER BY created_at DESC
                """,
                (str(days),),
            )
            rows = cursor.fetchall()
        result: list[RatingRecord] = []
        for row in rows:
            created_at = row["created_at"]
            if not isinstance(created_at, datetime):
                created_at = datetime.fromisoformat(str(created_at))
            result.append(
                RatingRecord(
                    rating_id=str(row["id"]),
                    user_id=str(row["user_id"]) if row.get("user_id") else None,
                    feature=row["feature"],
                    rating=int(row["rating"]),
                    source_text=row.get("source_text"),
                    result_text=row.get("result_text"),
                    direction=row.get("direction"),
                    created_at=created_at,
                )
            )
        return result
    except Exception:
        logger.exception("Failed to load translation_ratings summary")
        return list(_memory_ratings)
