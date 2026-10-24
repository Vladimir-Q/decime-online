from typing import Literal

from pydantic import BaseModel, Field

RatingFeature = Literal["quick_reply", "live_chat"]
RatingValue = Literal[-1, 0, 1]


class TranslationRatingRequest(BaseModel):
    feature: RatingFeature
    rating: RatingValue
    source_text: str | None = Field(default=None, max_length=4000)
    result_text: str | None = Field(default=None, max_length=4000)
    direction: str | None = Field(default=None, max_length=64)


class TranslationRatingResponse(BaseModel):
    rating_id: str
    feature: RatingFeature
    rating: RatingValue


class AdminUsageSummary(BaseModel):
    days: int
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    known_cost_usd: float = 0.0
    legacy_unverified_cost_usd: float = 0.0
    unknown_price_calls: int = 0
    pricing_version: str | None = None
    by_operation: dict[str, dict]


class AdminRatingsSummary(BaseModel):
    days: int
    total: int
    counts: dict[str, int]
    average_score: float
    by_feature: dict[str, dict[str, int]]


class AdminDashboardResponse(BaseModel):
    usage: AdminUsageSummary
    ratings: AdminRatingsSummary
