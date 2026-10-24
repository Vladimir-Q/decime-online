import asyncio

from decime_api.db.training import get_training_repository
from decime_api.db.user_store import get_user_store
from decime_api.dependencies import get_training_extractor
from decime_api.schemas.training import ExtractCandidatesRequest
from decime_api.services.training.training_service import extract_training_candidates


async def main() -> None:
    users = get_user_store().list_users()
    if not users:
        print("ERR no users")
        return
    user_id = users[0].id
    repo = get_training_repository()
    list_id = repo.get_default_list_id(user_id)
    req = ExtractCandidatesRequest(
        source_type="generated_reply",
        source_language="ru",
        source_original_text="test",
        spanish_text=(
            "Hola, me llamo Vladimir, vivo en la calle 18 de Julio. "
            "Me trajeron 25 bombillas para mate, ¡qué locura!"
        ),
        list_id=list_id,
    )
    try:
        result = await extract_training_candidates(
            user_id,
            req,
            extractor=get_training_extractor(),
            repository=repo,
        )
        print("OK", len(result.candidates), result.extraction_id[:8])
    except Exception as error:
        print("ERR", type(error).__name__, str(error)[:500])


if __name__ == "__main__":
    asyncio.run(main())
