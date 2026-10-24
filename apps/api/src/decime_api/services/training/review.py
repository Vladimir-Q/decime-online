from datetime import UTC, datetime

from decime_api.config import settings
from decime_api.db.training import TrainingItemRecord, TrainingRepository
from decime_api.schemas.training import (
    ReviewMode,
    ReviewNextResponse,
    ReviewQueueItem,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    TrainingCandidate,
)
from decime_api.services.training.scheduler import compute_next_schedule


def build_review_modes(item: TrainingItemRecord) -> list[ReviewMode]:
    modes: list[ReviewMode] = ["ru_to_es", "es_to_ru"]
    if item.audio_id and item.audio_status == "ready":
        modes.append("audio_to_meaning")
    if build_grammar_prompt(item.candidate):
        modes.append("grammar_prompt")
    return modes


def build_grammar_prompt(candidate: TrainingCandidate) -> str | None:
    grammar = candidate.grammar or {}
    if candidate.item_type == "noun":
        return "noun + article"
    if candidate.item_type == "adjective":
        gender = grammar.get("gender")
        number = grammar.get("number")
        if gender and number:
            return f"{gender} {number}"
        return "adjective form"
    if candidate.item_type == "verb_form":
        pronoun = grammar.get("pronoun")
        tense = grammar.get("tense")
        lemma = candidate.lemma or candidate.display_text
        if grammar.get("voseo"):
            pronoun = "vos"
        parts = [part for part in (pronoun, lemma, tense) if part]
        if parts:
            return " + ".join(str(part) for part in parts)
        return "verb form"
    if candidate.item_type == "verb_infinitive":
        return "infinitive"
    if candidate.item_type == "idiom":
        return "idiom"
    if candidate.item_type == "expression":
        return "expression"
    return None


def build_review_queue_item(item: TrainingItemRecord) -> ReviewQueueItem:
    candidate = item.candidate
    prompt_ru = " / ".join(candidate.translations_ru) if candidate.translations_ru else candidate.display_text
    prompt_en = " / ".join(candidate.translations_en) if candidate.translations_en else None
    audio_url = (
        f"{settings.api_base_url}/api/v1/audio/files/{item.audio_id}"
        if item.audio_id
        else None
    )
    return ReviewQueueItem(
        item_id=item.item_id,
        item_type=candidate.item_type,
        display_text=candidate.display_text,
        prompt_ru=prompt_ru,
        prompt_en=prompt_en,
        grammar_prompt=build_grammar_prompt(candidate),
        audio_url=audio_url,
        review_modes=build_review_modes(item),
        review_stage=item.review_stage,
    )


async def get_review_next(
    *,
    user_id: str,
    list_id: str,
    limit: int,
    repository: TrainingRepository,
) -> ReviewNextResponse:
    now = datetime.now(UTC)
    due_items = await repository.get_due_items(user_id, list_id, limit=limit, now=now)
    remaining_due = await repository.count_due_items(user_id, list_id, now=now)
    return ReviewNextResponse(
        items=[build_review_queue_item(item) for item in due_items],
        due_count=remaining_due,
    )


async def submit_review(
    user_id: str,
    request: ReviewSubmitRequest,
    *,
    repository: TrainingRepository,
) -> ReviewSubmitResponse:
    item = await repository.get_item(user_id, request.item_id)
    if item is None:
        raise ValueError("Training item not found")

    stage, next_review_at = compute_next_schedule(
        current_stage=item.review_stage,
        grade=request.grade,
    )
    await repository.update_item_schedule(
        user_id,
        item_id=item.item_id,
        review_stage=stage,
        next_review_at=next_review_at,
    )
    await repository.record_review_attempt(
        user_id,
        item_id=item.item_id,
        review_mode=request.review_mode,
        grade=request.grade,
        response_latency_ms=request.response_latency_ms,
        used_hint=request.used_hint,
    )

    from decime_api.services.analytics.event_log import EVENT_REVIEW_COMPLETED, log_event

    await log_event(
        user_id,
        EVENT_REVIEW_COMPLETED,
        {"item_id": item.item_id, "grade": request.grade},
    )

    now = datetime.now(UTC)
    remaining_due = await repository.count_due_items(user_id, item.list_id, now=now)
    return ReviewSubmitResponse(
        item_id=item.item_id,
        review_stage=stage,
        next_review_at=next_review_at.isoformat(),
        remaining_due=remaining_due,
    )
