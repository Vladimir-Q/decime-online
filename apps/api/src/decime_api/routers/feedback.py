from typing import Annotated

from fastapi import APIRouter, Depends, Query

from decime_api.auth.dependencies import CurrentUser, get_current_user, require_admin
from decime_api.auth.user_scope import resolve_user_id
from decime_api.schemas.feedback import (
    AdminDashboardResponse,
    AdminRatingsSummary,
    AdminUsageSummary,
    TranslationRatingRequest,
    TranslationRatingResponse,
)
from decime_api.services.analytics.llm_usage import summarize_usage
from decime_api.services.analytics.ratings import save_translation_rating, summarize_ratings

router = APIRouter(tags=["feedback"])


@router.post("/feedback/translation-rating", response_model=TranslationRatingResponse)
async def submit_translation_rating(
    request: TranslationRatingRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> TranslationRatingResponse:
    user_id = resolve_user_id(user)
    record = await save_translation_rating(
        user_id=user_id,
        feature=request.feature,
        rating=request.rating,
        source_text=request.source_text,
        result_text=request.result_text,
        direction=request.direction,
    )
    return TranslationRatingResponse(
        rating_id=record.rating_id,
        feature=request.feature,
        rating=request.rating,
    )


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    _admin: Annotated[CurrentUser, Depends(require_admin)],
    days: int = Query(default=30, ge=1, le=365),
) -> AdminDashboardResponse:
    usage = summarize_usage(days=days)
    ratings = summarize_ratings(days=days)
    return AdminDashboardResponse(
        usage=AdminUsageSummary(**usage),
        ratings=AdminRatingsSummary(**ratings),
    )
