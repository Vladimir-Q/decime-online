from decime_api.config import settings
from decime_api.services.compose.reply_composer import HistoryRepository, MemoryHistoryRepository

_history_repository: HistoryRepository | None = None


def get_history_repository() -> HistoryRepository:
    global _history_repository
    if _history_repository is not None:
        return _history_repository

    if settings.use_postgres:
        from decime_api.db.postgres_history import PostgresHistoryRepository

        _history_repository = PostgresHistoryRepository()
    else:
        _history_repository = MemoryHistoryRepository()

    return _history_repository


def reset_history_repository() -> None:
    global _history_repository
    _history_repository = None
