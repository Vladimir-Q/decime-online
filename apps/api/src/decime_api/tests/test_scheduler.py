from datetime import UTC, datetime, timedelta

from decime_api.services.training.scheduler import (
    MAX_REVIEW_STAGE,
    REVIEW_STAGES_SECONDS,
    compute_next_schedule,
)


def test_good_advances_stage() -> None:
    stage, next_at = compute_next_schedule(
        current_stage=0,
        grade="good",
        now=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
    )
    assert stage == 1
    assert next_at == datetime(2026, 5, 28, 12, 0, tzinfo=UTC) + timedelta(
        seconds=REVIEW_STAGES_SECONDS[1]
    )


def test_easy_advances_two_stages() -> None:
    stage, _ = compute_next_schedule(current_stage=1, grade="easy")
    assert stage == 3


def test_again_regresses_stage() -> None:
    stage, next_at = compute_next_schedule(
        current_stage=3,
        grade="again",
        now=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
    )
    assert stage == 2
    assert next_at == datetime(2026, 5, 28, 12, 0, tzinfo=UTC) + timedelta(
        seconds=REVIEW_STAGES_SECONDS[1]
    )


def test_again_at_stage_zero_stays_zero() -> None:
    stage, _ = compute_next_schedule(current_stage=0, grade="again")
    assert stage == 0


def test_hard_keeps_stage() -> None:
    stage, next_at = compute_next_schedule(
        current_stage=2,
        grade="hard",
        now=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
    )
    assert stage == 2
    assert next_at == datetime(2026, 5, 28, 12, 0, tzinfo=UTC) + timedelta(
        seconds=REVIEW_STAGES_SECONDS[2]
    )


def test_stage_capped_at_max() -> None:
    stage, _ = compute_next_schedule(current_stage=MAX_REVIEW_STAGE, grade="easy")
    assert stage == MAX_REVIEW_STAGE
