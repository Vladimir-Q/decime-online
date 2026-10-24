from datetime import UTC, datetime, timedelta

ReviewGrade = str

REVIEW_STAGES_SECONDS = [
    0,
    10 * 60,
    24 * 60 * 60,
    3 * 24 * 60 * 60,
    7 * 24 * 60 * 60,
    14 * 24 * 60 * 60,
    30 * 24 * 60 * 60,
]

MAX_REVIEW_STAGE = len(REVIEW_STAGES_SECONDS) - 1


def compute_next_schedule(
    *,
    current_stage: int,
    grade: ReviewGrade,
    now: datetime | None = None,
) -> tuple[int, datetime]:
    moment = now or datetime.now(UTC)
    stage = max(0, min(current_stage, MAX_REVIEW_STAGE))

    if grade == "again":
        stage = max(stage - 1, 0)
        delay = REVIEW_STAGES_SECONDS[1]
    elif grade == "hard":
        delay = REVIEW_STAGES_SECONDS[stage]
    elif grade == "good":
        stage = min(stage + 1, MAX_REVIEW_STAGE)
        delay = REVIEW_STAGES_SECONDS[stage]
    elif grade == "easy":
        stage = min(stage + 2, MAX_REVIEW_STAGE)
        delay = REVIEW_STAGES_SECONDS[stage]
    else:
        raise ValueError(f"Unknown review grade: {grade}")

    if delay == 0:
        return stage, moment
    return stage, moment + timedelta(seconds=delay)
