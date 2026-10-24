import asyncio

from decime_api.dependencies import get_training_extractor
from decime_api.schemas.training import ExtractCandidatesRequest


async def main() -> None:
    req = ExtractCandidatesRequest(
        source_type="generated_reply",
        source_language="ru",
        spanish_text="Hola, me llamo Vladimir, vivo en la calle 18 de Julio.",
    )
    ext = get_training_extractor()
    try:
        bundle = await ext.extract_candidates(req)
        print("OK candidates", len(bundle.candidates))
        for c in bundle.candidates[:5]:
            print(c.item_type, c.display_text)
    except Exception as error:
        print("ERR", type(error).__name__, error)


if __name__ == "__main__":
    asyncio.run(main())
