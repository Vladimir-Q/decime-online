import pytest

from decime_api.db.training import MemoryTrainingRepository, TrainingItemRecord
from decime_api.schemas.training import ExtractCandidatesRequest
from decime_api.services.ai.fake_training_extractor import FakeTrainingExtractor
from decime_api.services.training.training_service import extract_training_candidates


@pytest.mark.asyncio
async def test_training_items_isolated_by_user_id() -> None:
    repo = MemoryTrainingRepository()
    extractor = FakeTrainingExtractor()
    user_a = "11111111-1111-4111-8111-111111111111"
    user_b = "22222222-2222-4222-8222-222222222222"

    request = ExtractCandidatesRequest(
        source_type="generated_reply",
        source_language="ru",
        spanish_text="Quería consultar si se puede pagar con tarjeta.",
    )

    result_a = await extract_training_candidates(
        user_a, request, extractor=extractor, repository=repo
    )
    list_a = repo.get_default_list_id(user_a)

    from decime_api.services.training.canonical import build_canonical_key

    candidate = result_a.candidates[0]
    canonical = build_canonical_key(
        item_type=candidate.item_type,
        surface_text=candidate.surface_text,
        lemma=candidate.lemma,
        grammar=candidate.grammar,
    )
    await repo.add_items(
        user_a,
        [
            TrainingItemRecord(
                item_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                list_id=list_a,
                candidate=candidate,
                canonical_key=canonical,
            )
        ],
    )

    items_a = await repo.list_items(user_a, list_a)
    items_b = await repo.list_items(user_b, repo.get_default_list_id(user_b))

    assert len(items_a) == 1
    assert len(items_b) == 0

    assert await repo.get_item(user_b, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") is None
    assert await repo.get_item(user_a, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") is not None
