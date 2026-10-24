from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from decime_api.config import settings
from decime_api.schemas.training import ReviewGrade, ReviewMode, TrainingCandidate


@dataclass
class TrainingListRecord:
    list_id: str
    name: str
    locale_variant: str
    item_count: int = 0


@dataclass
class ExtractionRecord:
    extraction_id: str
    source_type: str
    source_language: str
    source_original_text: str | None
    spanish_text: str
    target_locale: str
    candidates: list[TrainingCandidate]
    provider: str
    model: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TrainingItemRecord:
    item_id: str
    list_id: str
    candidate: TrainingCandidate
    canonical_key: str
    audio_id: str | None = None
    audio_status: str = "none"
    review_stage: int = 0
    next_review_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ReviewAttemptRecord:
    item_id: str
    review_mode: ReviewMode
    grade: ReviewGrade
    response_latency_ms: int
    used_hint: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TrainingRepository(Protocol):
    def get_default_list_id(self, user_id: str) -> str: ...

    async def list_lists(self, user_id: str) -> list[TrainingListRecord]: ...

    async def list_items(self, user_id: str, list_id: str) -> list[TrainingItemRecord]: ...

    async def get_item(self, user_id: str, item_id: str) -> TrainingItemRecord | None: ...

    async def get_due_items(
        self,
        user_id: str,
        list_id: str,
        *,
        limit: int,
        now: datetime,
    ) -> list[TrainingItemRecord]: ...

    async def count_due_items(self, user_id: str, list_id: str, *, now: datetime) -> int: ...

    async def update_item_schedule(
        self,
        user_id: str,
        *,
        item_id: str,
        review_stage: int,
        next_review_at: datetime,
    ) -> None: ...

    async def record_review_attempt(
        self,
        user_id: str,
        *,
        item_id: str,
        review_mode: ReviewMode,
        grade: ReviewGrade,
        response_latency_ms: int,
        used_hint: bool,
    ) -> None: ...

    async def get_known_canonical_keys(
        self, user_id: str, list_id: str | None = None
    ) -> set[str]: ...

    async def save_extraction(self, user_id: str, record: ExtractionRecord) -> None: ...

    async def get_extraction(self, user_id: str, extraction_id: str) -> ExtractionRecord | None: ...

    async def add_items(self, user_id: str, items: list[TrainingItemRecord]) -> None: ...

    async def delete_item(self, user_id: str, item_id: str) -> bool: ...

    async def update_item_audio(
        self,
        user_id: str,
        *,
        item_id: str,
        audio_id: str,
        audio_status: str = "ready",
    ) -> TrainingItemRecord | None: ...

    async def clear(self, user_id: str) -> None: ...


class MemoryTrainingRepository:
    def __init__(self) -> None:
        self._lists: dict[str, dict[str, TrainingListRecord]] = {}
        self._extractions: dict[str, ExtractionRecord] = {}
        self._items: dict[str, TrainingItemRecord] = {}
        self._attempts: list[ReviewAttemptRecord] = []
        self._item_owners: dict[str, str] = {}
        self._extraction_owners: dict[str, str] = {}

    def _ensure_default_list(self, user_id: str) -> TrainingListRecord:
        user_lists = self._lists.setdefault(user_id, {})
        for record in user_lists.values():
            if record.name == "My phrases":
                return record
        list_id = str(uuid4())
        user_lists[list_id] = TrainingListRecord(
            list_id=list_id,
            name="My phrases",
            locale_variant="es-UY-montevideo",
            item_count=0,
        )
        return user_lists[list_id]

    def get_default_list_id(self, user_id: str) -> str:
        return self._ensure_default_list(user_id).list_id

    async def list_lists(self, user_id: str) -> list[TrainingListRecord]:
        self._ensure_default_list(user_id)
        records = list(self._lists.get(user_id, {}).values())
        for record in records:
            record.item_count = sum(
                1
                for item_id, owner in self._item_owners.items()
                if owner == user_id and self._items[item_id].list_id == record.list_id
            )
        return records

    async def list_items(self, user_id: str, list_id: str) -> list[TrainingItemRecord]:
        self._assert_list_owner(user_id, list_id)
        return [
            item
            for item_id, item in self._items.items()
            if self._item_owners.get(item_id) == user_id and item.list_id == list_id
        ]

    async def get_item(self, user_id: str, item_id: str) -> TrainingItemRecord | None:
        if self._item_owners.get(item_id) != user_id:
            return None
        return self._items.get(item_id)

    async def get_due_items(
        self,
        user_id: str,
        list_id: str,
        *,
        limit: int,
        now: datetime,
    ) -> list[TrainingItemRecord]:
        self._assert_list_owner(user_id, list_id)
        due = [
            item
            for item_id, item in self._items.items()
            if self._item_owners.get(item_id) == user_id
            and item.list_id == list_id
            and item.next_review_at <= now
        ]
        due.sort(key=lambda item: (item.next_review_at, item.created_at))
        return due[:limit]

    async def count_due_items(self, user_id: str, list_id: str, *, now: datetime) -> int:
        self._assert_list_owner(user_id, list_id)
        return sum(
            1
            for item_id, item in self._items.items()
            if self._item_owners.get(item_id) == user_id
            and item.list_id == list_id
            and item.next_review_at <= now
        )

    async def update_item_schedule(
        self,
        user_id: str,
        *,
        item_id: str,
        review_stage: int,
        next_review_at: datetime,
    ) -> None:
        if self._item_owners.get(item_id) != user_id:
            raise ValueError("Training item not found")
        item = self._items.get(item_id)
        if item is None:
            raise ValueError("Training item not found")
        item.review_stage = review_stage
        item.next_review_at = next_review_at

    async def record_review_attempt(
        self,
        user_id: str,
        *,
        item_id: str,
        review_mode: ReviewMode,
        grade: ReviewGrade,
        response_latency_ms: int,
        used_hint: bool,
    ) -> None:
        if self._item_owners.get(item_id) != user_id:
            raise ValueError("Training item not found")
        self._attempts.append(
            ReviewAttemptRecord(
                item_id=item_id,
                review_mode=review_mode,
                grade=grade,
                response_latency_ms=response_latency_ms,
                used_hint=used_hint,
            )
        )

    async def get_known_canonical_keys(
        self, user_id: str, list_id: str | None = None
    ) -> set[str]:
        keys: set[str] = set()
        for item_id, item in self._items.items():
            if self._item_owners.get(item_id) != user_id:
                continue
            if list_id and item.list_id != list_id:
                continue
            keys.add(item.canonical_key)
        return keys

    async def save_extraction(self, user_id: str, record: ExtractionRecord) -> None:
        self._extractions[record.extraction_id] = record
        self._extraction_owners[record.extraction_id] = user_id

    async def get_extraction(self, user_id: str, extraction_id: str) -> ExtractionRecord | None:
        if self._extraction_owners.get(extraction_id) != user_id:
            return None
        return self._extractions.get(extraction_id)

    async def add_items(self, user_id: str, items: list[TrainingItemRecord]) -> None:
        for item in items:
            self._items[item.item_id] = item
            self._item_owners[item.item_id] = user_id
        default_list = self._ensure_default_list(user_id)
        default_list.item_count = sum(
            1
            for item_id, owner in self._item_owners.items()
            if owner == user_id and self._items[item_id].list_id == default_list.list_id
        )

    async def delete_item(self, user_id: str, item_id: str) -> bool:
        if self._item_owners.get(item_id) != user_id:
            return False
        self._items.pop(item_id, None)
        self._item_owners.pop(item_id, None)
        if user_id in self._lists:
            for list_record in self._lists[user_id].values():
                list_record.item_count = sum(
                    1
                    for owned_id, owner in self._item_owners.items()
                    if owner == user_id and self._items[owned_id].list_id == list_record.list_id
                )
        return True

    async def update_item_audio(
        self,
        user_id: str,
        *,
        item_id: str,
        audio_id: str,
        audio_status: str = "ready",
    ) -> TrainingItemRecord | None:
        if self._item_owners.get(item_id) != user_id:
            return None
        item = self._items.get(item_id)
        if item is None:
            return None
        item.audio_id = audio_id
        item.audio_status = audio_status
        return item

    async def clear(self, user_id: str) -> None:
        to_delete = [item_id for item_id, owner in self._item_owners.items() if owner == user_id]
        for item_id in to_delete:
            self._items.pop(item_id, None)
            self._item_owners.pop(item_id, None)
        to_delete_ext = [
            ext_id for ext_id, owner in self._extraction_owners.items() if owner == user_id
        ]
        for ext_id in to_delete_ext:
            self._extractions.pop(ext_id, None)
            self._extraction_owners.pop(ext_id, None)
        if user_id in self._lists:
            for list_record in self._lists[user_id].values():
                list_record.item_count = 0

    def _assert_list_owner(self, user_id: str, list_id: str) -> None:
        user_lists = self._lists.get(user_id, {})
        if list_id not in user_lists:
            raise ValueError("Training list not found")


_repository: TrainingRepository | None = None


def get_training_repository() -> TrainingRepository:
    global _repository
    if _repository is None:
        if settings.use_postgres:
            from decime_api.db.postgres_training import PostgresTrainingRepository

            _repository = PostgresTrainingRepository()
        else:
            _repository = MemoryTrainingRepository()
    return _repository


def reset_training_repository() -> None:
    global _repository
    _repository = None
