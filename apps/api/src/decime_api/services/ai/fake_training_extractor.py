from uuid import uuid4

from decime_api.schemas.training import (
    ExtractCandidatesRequest,
    ExtractionBundle,
    TrainingCandidate,
)
from decime_api.services.ai.normalize_parse import parse_normalized_candidate
from decime_api.services.training.display_text import strip_leading_article


class FakeTrainingExtractor:
    provider_name = "fake"
    model_name = "fake-extract-v1"

    async def extract_candidates(self, request: ExtractCandidatesRequest) -> ExtractionBundle:
        text = request.spanish_text
        lower = text.lower()
        candidates: list[TrainingCandidate] = []

        if "tarjeta" in lower:
            candidates.extend(_card_payment_candidates(text, request))
        elif "mando" in lower or "mand" in lower:
            candidates.extend(_invoice_reply_candidates(text, request))
        else:
            candidates.append(
                TrainingCandidate(
                    candidate_id=str(uuid4()),
                    item_type="verb_form",
                    surface_text="consultar",
                    display_text="consultar",
                    lemma="consultar",
                    translations_ru=["уточнять", "спрашивать"],
                    translations_en=["to ask", "to check"],
                    example_es=text,
                    status_hint="new",
                )
            )

        filtered = [
            candidate
            for candidate in candidates
            if candidate.item_type in request.candidate_types
        ]
        return ExtractionBundle(
            target_locale=request.target_locale,
            source_language=request.source_language,
            spanish_text=text,
            candidates=filtered,
            skipped_reasoning_summary=["fake_extractor_response"],
        )

    async def normalize_dictionary_row(
        self,
        *,
        spanish: str,
        russian: str | None = None,
        target_locale: str = "es-UY-montevideo",
    ) -> TrainingCandidate:
        text = spanish.strip()
        lower = text.lower()
        raw: dict
        if "dar la lata" in lower or "idiom" in lower:
            raw = {
                "item_type": "idiom",
                "surface_text": text,
                "display_text": text,
                "lemma": text,
                "translations_ru": ["доставать", "надоедать"],
                "translations_en": ["to bother"],
                "grammar": {},
                "governance": [],
                "example_es": text,
                "status_hint": "new",
            }
        elif "por favor" in lower or "expression" in lower:
            raw = {
                "item_type": "expression",
                "surface_text": text,
                "display_text": text,
                "lemma": text,
                "translations_ru": ["пожалуйста"],
                "translations_en": ["please"],
                "grammar": {},
                "governance": [],
                "example_es": text,
                "status_hint": "new",
            }
        elif "bonit" in lower:
            raw = {
                "item_type": "adjective",
                "surface_text": text,
                "display_text": text,
                "lemma": "bonito",
                "translations_ru": ["красивый"],
                "translations_en": ["pretty"],
                "grammar": {"gender": "masculine", "number": "singular"},
                "governance": [],
                "example_es": text,
                "status_hint": "new",
            }
        elif any(token in lower for token in ("quería", "puedo", "vas", "podés")):
            raw = {
                "item_type": "verb_form",
                "surface_text": text,
                "display_text": text,
                "lemma": "querer" if "quer" in lower else "poder",
                "translations_ru": ["форма глагола"],
                "translations_en": ["verb form"],
                "grammar": {
                    "pronoun": "yo",
                    "person": 1,
                    "number": "singular",
                    "tense": "presente",
                    "mood": "indicativo",
                    "voseo": False,
                },
                "governance": [],
                "example_es": text,
                "status_hint": "new",
            }
        elif "pagar" in lower and " " not in text.strip():
            raw = {
                "item_type": "verb_infinitive",
                "surface_text": text,
                "display_text": text,
                "lemma": "pagar",
                "translations_ru": ["платить"],
                "translations_en": ["to pay"],
                "grammar": {},
                "governance": [],
                "example_es": text,
                "status_hint": "new",
            }
        else:
            # Noun path: grammar.article may be set while display lacks article (DB pattern).
            lemma = strip_leading_article(text) or text
            article = "la" if lemma.endswith("a") else "el"
            raw = {
                "item_type": "noun",
                "surface_text": lemma,
                "display_text": lemma,
                "lemma": lemma,
                "translations_ru": ["перевод"],
                "translations_en": ["translation"],
                "grammar": {"article": article, "gender": "feminine" if article == "la" else "masculine", "number": "singular"},
                "governance": [],
                "example_es": text,
                "status_hint": "new",
            }
        return parse_normalized_candidate(
            raw,
            spanish=text,
            russian=russian,
            target_locale=target_locale,
        )


def _card_payment_candidates(text: str, request: ExtractCandidatesRequest) -> list[TrainingCandidate]:
    example_ru = request.source_original_text
    return [
        TrainingCandidate(
            candidate_id=str(uuid4()),
            item_type="verb_form",
            surface_text="quería",
            display_text="yo quería",
            lemma="querer",
            translations_ru=["я хотел", "я хотела"],
            translations_en=["I wanted"],
            context_translation_ru="вежливая смягчающая форма",
            grammar={
                "pronoun": "yo",
                "person": 1,
                "number": "singular",
                "tense": "pretérito imperfecto",
                "mood": "indicativo",
                "voseo": False,
            },
            governance=["querer + infinitivo"],
            example_es=text,
            example_ru=example_ru,
            status_hint="new",
        ),
        TrainingCandidate(
            candidate_id=str(uuid4()),
            item_type="noun",
            surface_text="la tarjeta",
            display_text="la tarjeta",
            lemma="tarjeta",
            translations_ru=["карта"],
            translations_en=["card"],
            grammar={"article": "la", "gender": "feminine", "number": "singular"},
            example_es=text,
            example_ru=example_ru,
            status_hint="new",
        ),
        TrainingCandidate(
            candidate_id=str(uuid4()),
            item_type="verb_infinitive",
            surface_text="pagar",
            display_text="pagar",
            lemma="pagar",
            translations_ru=["платить"],
            translations_en=["to pay"],
            governance=["pagar con + sustantivo"],
            example_es=text,
            example_ru=example_ru,
            status_hint="new",
        ),
    ]


def _invoice_reply_candidates(text: str, request: ExtractCandidatesRequest) -> list[TrainingCandidate]:
    return [
        TrainingCandidate(
            candidate_id=str(uuid4()),
            item_type="verb_form",
            surface_text="mando",
            display_text="te la mando",
            lemma="mandar",
            translations_ru=["отправляю"],
            translations_en=["I send"],
            grammar={
                "pronoun": "yo",
                "person": 1,
                "number": "singular",
                "tense": "presente",
                "mood": "indicativo",
                "voseo": False,
            },
            example_es=text,
            example_ru=request.source_original_text,
            status_hint="new",
        ),
        TrainingCandidate(
            candidate_id=str(uuid4()),
            item_type="noun",
            surface_text="la factura",
            display_text="la factura",
            lemma="factura",
            translations_ru=["счёт", "инвойс"],
            translations_en=["invoice"],
            grammar={"article": "la", "gender": "feminine", "number": "singular"},
            example_es=text,
            status_hint="new",
        ),
    ]
