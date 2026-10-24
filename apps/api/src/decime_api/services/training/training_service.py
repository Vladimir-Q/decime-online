from datetime import UTC, datetime
from uuid import uuid4

from decime_api.db.postgres_audio import register_audio_file
from decime_api.db.training import ExtractionRecord, TrainingItemRecord, TrainingRepository
from decime_api.schemas.audio import SynthesizeAudioRequest
from decime_api.schemas.training import (
    AddToVocabRequest,
    AddToVocabResponse,
    ApproveCandidatesRequest,
    ApproveCandidatesResponse,
    CreatedTrainingItem,
    ExtractCandidatesRequest,
    ExtractCandidatesResponse,
    ItemAudioResponse,
    TrainingCandidate,
    TrainingListSummary,
)
from decime_api.services.ai.speech_provider import TTSProvider
from decime_api.services.ai.training_extractor import TrainingExtractor
from decime_api.services.audio.audio_service import synthesize_text
from decime_api.services.locale import normalize_locale_variant
from decime_api.services.storage.audio_storage import LocalAudioStorage
from decime_api.services.training.canonical import build_canonical_key


async def extract_training_candidates(
    user_id: str,
    request: ExtractCandidatesRequest,
    *,
    extractor: TrainingExtractor,
    repository: TrainingRepository,
) -> ExtractCandidatesResponse:
    bundle = await extractor.extract_candidates(request)
    list_id = request.list_id or repository.get_default_list_id(user_id)
    known_keys = await repository.get_known_canonical_keys(user_id, list_id)

    candidates: list[TrainingCandidate] = []
    for raw in bundle.candidates:
        canonical = build_canonical_key(
            item_type=raw.item_type,
            surface_text=raw.surface_text,
            lemma=raw.lemma,
            grammar=raw.grammar,
        )
        status_hint = raw.status_hint
        if canonical in known_keys:
            status_hint = "duplicate_possible"

        candidates.append(
            raw.model_copy(
                update={
                    "candidate_id": raw.candidate_id or str(uuid4()),
                    "locale_variant": normalize_locale_variant(
                        raw.locale_variant or request.target_locale
                    ),
                    "canonical_key": canonical,
                    "status_hint": status_hint,
                    "example_es": raw.example_es or request.spanish_text,
                }
            )
        )

    extraction_id = str(uuid4())
    await repository.save_extraction(
        user_id,
        ExtractionRecord(
            extraction_id=extraction_id,
            source_type=request.source_type,
            source_language=request.source_language,
            source_original_text=request.source_original_text,
            spanish_text=request.spanish_text,
            target_locale=request.target_locale,
            candidates=candidates,
            provider=extractor.provider_name,
            model=extractor.model_name,
        ),
    )
    return ExtractCandidatesResponse(extraction_id=extraction_id, candidates=candidates)


async def approve_training_candidates(
    user_id: str,
    request: ApproveCandidatesRequest,
    *,
    repository: TrainingRepository,
    tts: TTSProvider,
    storage: LocalAudioStorage,
) -> ApproveCandidatesResponse:
    extraction = await repository.get_extraction(user_id, request.extraction_id)
    if extraction is None:
        raise ValueError("Extraction not found")

    approved_ids = set(request.approved_candidate_ids)
    selected = [c for c in extraction.candidates if c.candidate_id in approved_ids]

    known_keys = await repository.get_known_canonical_keys(user_id, request.list_id)
    created: list[CreatedTrainingItem] = []
    skipped_duplicates: list[str] = []
    new_items: list[TrainingItemRecord] = []

    for candidate in selected:
        canonical = candidate.canonical_key or build_canonical_key(
            item_type=candidate.item_type,
            surface_text=candidate.surface_text,
            lemma=candidate.lemma,
            grammar=candidate.grammar,
        )
        if canonical in known_keys:
            skipped_duplicates.append(candidate.display_text)
            continue

        item_id = str(uuid4())
        audio_id: str | None = None
        audio_status = "none"

        if request.generate_audio:
            synth = await synthesize_text(
                user_id,
                SynthesizeAudioRequest(
                    text=candidate.display_text,
                    locale=extraction.target_locale,
                    mode="training_reference",
                    speed="normal",
                ),
                tts=tts,
                storage=storage,
            )
            audio_id = synth.audio_id
            audio_status = "ready"

        new_items.append(
            TrainingItemRecord(
                item_id=item_id,
                list_id=request.list_id,
                candidate=candidate,
                canonical_key=canonical,
                audio_id=audio_id,
                audio_status=audio_status,
                review_stage=0,
                next_review_at=datetime.now(UTC),
            )
        )
        known_keys.add(canonical)
        created.append(
            CreatedTrainingItem(
                item_id=item_id,
                surface_text=candidate.display_text,
                audio_status=audio_status,
            )
        )

    if new_items:
        await repository.add_items(user_id, new_items)

    from decime_api.services.analytics.event_log import EVENT_CANDIDATE_APPROVED, log_event

    await log_event(
        user_id,
        EVENT_CANDIDATE_APPROVED,
        {"count": len(created), "list_id": request.list_id},
    )

    return ApproveCandidatesResponse(
        created_items=created,
        skipped_duplicates=skipped_duplicates,
    )


async def add_spanish_to_vocab(
    user_id: str,
    request: AddToVocabRequest,
    *,
    extractor: TrainingExtractor,
    repository: TrainingRepository,
    tts: TTSProvider,
    storage: LocalAudioStorage,
) -> AddToVocabResponse:
    list_id = request.list_id or repository.get_default_list_id(user_id)
    extraction = await extract_training_candidates(
        user_id,
        ExtractCandidatesRequest(
            source_type=request.source_type,
            source_language=request.source_language,
            source_original_text=request.source_original_text,
            spanish_text=request.spanish_text,
            target_locale=request.target_locale,
            list_id=list_id,
        ),
        extractor=extractor,
        repository=repository,
    )
    approved_ids = [
        candidate.candidate_id
        for candidate in extraction.candidates
        if candidate.candidate_id and candidate.status_hint != "duplicate_possible"
    ]
    if not approved_ids:
        return AddToVocabResponse(
            created_items=[],
            skipped_duplicates=[c.display_text for c in extraction.candidates],
            extraction_id=extraction.extraction_id,
        )

    result = await approve_training_candidates(
        user_id,
        ApproveCandidatesRequest(
            list_id=list_id,
            extraction_id=extraction.extraction_id,
            approved_candidate_ids=approved_ids,
            generate_audio=False,
        ),
        repository=repository,
        tts=tts,
        storage=storage,
    )
    return AddToVocabResponse(
        created_items=result.created_items,
        skipped_duplicates=result.skipped_duplicates,
        extraction_id=extraction.extraction_id,
    )


async def delete_training_item(
    user_id: str,
    item_id: str,
    *,
    repository: TrainingRepository,
) -> bool:
    return await repository.delete_item(user_id, item_id)


async def generate_item_audio(
    user_id: str,
    item_id: str,
    *,
    repository: TrainingRepository,
    tts: TTSProvider,
    storage: LocalAudioStorage,
) -> ItemAudioResponse:
    item = await repository.get_item(user_id, item_id)
    if item is None:
        raise ValueError("Training item not found")

    text = (item.candidate.display_text or item.candidate.surface_text or "").strip()
    if not text:
        raise ValueError("Item has no Spanish text to synthesize")

    synth = await synthesize_text(
        user_id,
        SynthesizeAudioRequest(
            text=text,
            locale=normalize_locale_variant(item.candidate.locale_variant),
            mode="training_reference",
            speed="normal",
        ),
        tts=tts,
        storage=storage,
    )
    register_audio_file(storage, synth.audio_id, user_id=user_id, source_type="tts")
    updated = await repository.update_item_audio(
        user_id,
        item_id=item_id,
        audio_id=synth.audio_id,
        audio_status="ready",
    )
    if updated is None:
        raise ValueError("Training item not found")

    return ItemAudioResponse(
        item_id=item_id,
        audio_id=synth.audio_id,
        audio_url=synth.audio_url,
        audio_status="ready",
    )


async def list_training_lists(
    user_id: str, repository: TrainingRepository
) -> list[TrainingListSummary]:
    now = datetime.now(UTC)
    records = await repository.list_lists(user_id)
    summaries: list[TrainingListSummary] = []
    for record in records:
        due_count = await repository.count_due_items(user_id, record.list_id, now=now)
        summaries.append(
            TrainingListSummary(
                list_id=record.list_id,
                name=record.name,
                item_count=record.item_count,
                due_count=due_count,
            )
        )
    return summaries
