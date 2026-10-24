from typing import Literal

from pydantic import BaseModel, Field

ItemType = Literal[
    "noun",
    "adjective",
    "verb_form",
    "verb_infinitive",
    "idiom",
    "expression",
]
ReviewMode = Literal["ru_to_es", "es_to_ru", "audio_to_meaning", "grammar_prompt"]
ReviewGrade = Literal["again", "hard", "good", "easy"]
CandidateStatusHint = Literal["new", "learning", "known", "ignored", "duplicate_possible"]
SourceType = Literal[
    "generated_reply",
    "transcript",
    "incoming_text",
    "manual",
]


class TrainingCandidate(BaseModel):
    candidate_id: str | None = None
    item_type: ItemType
    surface_text: str
    display_text: str
    lemma: str | None = None
    locale_variant: str = "es-UY-montevideo"
    translations_ru: list[str]
    translations_en: list[str]
    context_translation_ru: str | None = None
    context_translation_en: str | None = None
    grammar: dict = Field(default_factory=dict)
    governance: list[str] = Field(default_factory=list)
    example_es: str | None = None
    example_ru: str | None = None
    example_en: str | None = None
    status_hint: CandidateStatusHint = "new"
    canonical_key: str | None = None


class ExtractCandidatesRequest(BaseModel):
    source_type: SourceType
    source_language: str
    source_original_text: str | None = None
    spanish_text: str = Field(min_length=1)
    target_locale: str = "es-UY-montevideo"
    user_level: str = "A2"
    list_id: str | None = None
    candidate_types: list[ItemType] = Field(
        default_factory=lambda: ["noun", "adjective", "verb_form", "verb_infinitive"]
    )


class ExtractCandidatesResponse(BaseModel):
    extraction_id: str
    candidates: list[TrainingCandidate]


class ExtractionBundle(BaseModel):
    target_locale: str = "es-UY-montevideo"
    source_language: str
    spanish_text: str
    candidates: list[TrainingCandidate]
    skipped_reasoning_summary: list[str] = Field(default_factory=list)


class ApproveCandidatesRequest(BaseModel):
    list_id: str
    extraction_id: str
    approved_candidate_ids: list[str]
    generate_audio: bool = False


class CreatedTrainingItem(BaseModel):
    item_id: str
    surface_text: str
    audio_status: str


class ApproveCandidatesResponse(BaseModel):
    created_items: list[CreatedTrainingItem]
    skipped_duplicates: list[str] = Field(default_factory=list)


class TrainingListSummary(BaseModel):
    list_id: str
    name: str
    item_count: int = 0
    due_count: int = 0


class TrainingItemSummary(BaseModel):
    item_id: str
    list_id: str
    item_type: ItemType
    display_text: str
    translations_ru: list[str]
    translations_en: list[str]
    example_es: str | None = None
    audio_id: str | None = None
    audio_status: str = "none"
    review_stage: int = 0
    next_review_at: str | None = None
    created_at: str | None = None


class TrainingItemsResponse(BaseModel):
    items: list[TrainingItemSummary]


class AddToVocabRequest(BaseModel):
    spanish_text: str = Field(min_length=1)
    source_language: str = "ru"
    source_original_text: str | None = None
    source_type: SourceType = "generated_reply"
    target_locale: str = "es-UY-montevideo"
    list_id: str | None = None


class AddToVocabResponse(BaseModel):
    created_items: list[CreatedTrainingItem]
    skipped_duplicates: list[str] = Field(default_factory=list)
    extraction_id: str


class ItemAudioResponse(BaseModel):
    item_id: str
    audio_id: str
    audio_url: str
    audio_status: str


class ReviewQueueItem(BaseModel):
    item_id: str
    item_type: ItemType
    display_text: str
    prompt_ru: str
    prompt_en: str | None = None
    grammar_prompt: str | None = None
    audio_url: str | None = None
    review_modes: list[ReviewMode]
    review_stage: int = 0


class ReviewNextResponse(BaseModel):
    items: list[ReviewQueueItem]
    due_count: int = 0


class ReviewSubmitRequest(BaseModel):
    item_id: str
    review_mode: ReviewMode
    grade: ReviewGrade
    response_latency_ms: int = 0
    used_hint: bool = False


class ReviewSubmitResponse(BaseModel):
    item_id: str
    review_stage: int
    next_review_at: str
    remaining_due: int = 0


SheetsJobKind = Literal["export", "import"]
SheetsJobStatus = Literal["queued", "running", "completed", "failed"]
SheetsImportRowStatus = Literal["created", "skipped_duplicate", "error"]


class SheetsExportRequest(BaseModel):
    list_id: str


class SheetsImportRequest(BaseModel):
    list_id: str
    source_spreadsheet_id: str = Field(min_length=1)
    source_sheet_name: str = Field(min_length=1)


class SheetsJobAcceptedResponse(BaseModel):
    job_id: str
    status: SheetsJobStatus = "running"


class SheetsJobReport(BaseModel):
    created: int = 0
    skipped: int = 0
    errors: int = 0
    exported_rows: int | None = None
    updated_rows: int | None = None
    row_errors: list[dict] = Field(default_factory=list)
    partial: bool = False
    message: str | None = None


class SheetsJobStatusResponse(BaseModel):
    job_id: str
    kind: SheetsJobKind
    status: SheetsJobStatus
    list_id: str
    spreadsheet_id: str | None = None
    sheet_name: str | None = None
    source_spreadsheet_id: str | None = None
    source_sheet_name: str | None = None
    report: SheetsJobReport = Field(default_factory=SheetsJobReport)
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None


class N8nJobContextResponse(BaseModel):
    job_id: str
    kind: SheetsJobKind
    status: SheetsJobStatus
    user_id: str
    list_id: str
    spreadsheet_id: str | None = None
    sheet_name: str | None = None
    source_spreadsheet_id: str | None = None
    source_sheet_name: str | None = None
    max_import_rows: int
    report: SheetsJobReport = Field(default_factory=SheetsJobReport)


class N8nImportRowRequest(BaseModel):
    source_row_number: int = Field(ge=1)
    spanish: str = ""
    russian: str = ""


class N8nImportRowResponse(BaseModel):
    status: SheetsImportRowStatus
    item_id: str | None = None
    message: str | None = None


class N8nCompleteJobRequest(BaseModel):
    status: Literal["completed", "failed"]
    report: SheetsJobReport = Field(default_factory=SheetsJobReport)
    error_message: str | None = None
