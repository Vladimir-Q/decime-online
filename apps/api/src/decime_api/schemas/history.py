from pydantic import BaseModel


class HistoryItem(BaseModel):
    request_id: str
    created_at: str
    source_language: str | None
    source_text: str | None
    incoming_text: str | None
    channel: str | None
    tone: str | None
    situation: str | None
    recommended_reply: str
    dialect_stamp: str | None
    provider: str | None
    model: str | None


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
