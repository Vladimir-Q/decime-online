from typing import Protocol

from decime_api.schemas.training import (
    ExtractCandidatesRequest,
    ExtractionBundle,
    TrainingCandidate,
)


class TrainingExtractor(Protocol):
    provider_name: str
    model_name: str

    async def extract_candidates(self, request: ExtractCandidatesRequest) -> ExtractionBundle: ...

    async def normalize_dictionary_row(
        self,
        *,
        spanish: str,
        russian: str | None = None,
        target_locale: str = "es-UY-montevideo",
    ) -> TrainingCandidate: ...
