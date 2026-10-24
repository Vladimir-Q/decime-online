import asyncio

from decime_api.dependencies import get_training_extractor
from decime_api.db.training import get_training_repository
from decime_api.schemas.training import ExtractCandidatesRequest
from decime_api.services.training.training_service import extract_training_candidates


async def main() -> None:
    user_id = "00000000-0000-4000-8000-000000000099"
    req = ExtractCandidatesRequest(
        source_type="generated_reply",
        source_language="ru",
        spanish_text=(
            "Hola, me llamo Vladimir, vivo en la calle 18 de Julio. "
            "Me trajeron 25 bombillas para mate, ¡qué locura!"
        ),
    )
    try:
        result = await extract_training_candidates(
            user_id,
            req,
            extractor=get_training_extractor(),
            repository=get_training_repository(),
        )
        print("OK extraction_id", result.extraction_id, "count", len(result.candidates))
    except Exception as error:
        print("ERR", type(error).__name__, error)


if __name__ == "__main__":
    asyncio.run(main())
