"""Run Decime LLM evaluation suites against real provider implementations."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from decime_api.evals.dataset import load_cases
from decime_api.evals.deterministic import (
    evaluate_extract_case,
    evaluate_translate_case,
    evaluate_understand_case,
    summarize_checks,
)
from decime_api.evals.report import build_summary, write_report
from decime_api.schemas.compose import ReplyContext, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest
from decime_api.schemas.training import ExtractCandidatesRequest
from decime_api.services.ai.fake_llm import FakeLLMProvider
from decime_api.services.ai.fake_training_extractor import FakeTrainingExtractor

ProviderName = Literal["fake", "openai"]


def _prompt_meta_for_eval() -> dict[str, Any]:
    """Identity of the prompts this process would send. Old report files are not rewritten."""
    from decime_api.services.ai.lc.prompt_provider import eval_prompt_metadata

    return eval_prompt_metadata()


def _build_llm(provider: ProviderName, *, model: str | None = None):
    if provider == "fake":
        return FakeLLMProvider()
    if provider == "openai":
        from decime_api.config import settings
        from decime_api.services.ai.openai_llm import OpenAILLMProvider

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for provider=openai")
        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=model or settings.openai_text_model,
            base_url=settings.openai_text_base_url,
        )
    raise ValueError(f"Unknown provider: {provider}")


def _build_extractor(provider: ProviderName):
    if provider == "fake":
        return FakeTrainingExtractor()
    if provider == "openai":
        from decime_api.config import settings
        from decime_api.services.ai.openai_training_extractor import OpenAITrainingExtractor

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for provider=openai")
        return OpenAITrainingExtractor(
            api_key=settings.openai_api_key,
            model=settings.openai_text_model,
            base_url=settings.openai_text_base_url,
        )
    raise ValueError(f"Unknown provider: {provider}")


async def run_evaluation(
    *,
    provider: ProviderName = "fake",
    dataset_version: str = "v1",
    suites: list[str] | None = None,
    judge: bool = False,
    judge_model: str = "gpt-4o-mini",
    model: str | None = None,
    output_dir: Path | None = None,
    report_stem: str | None = None,
) -> dict[str, Any]:
    """Execute dataset cases against Decime providers and write a report.

    Text uses LangChain ChatOpenAI (``LLM_ORCHESTRATOR=langchain``).
    ``model`` overrides ``OPENAI_TEXT_MODEL`` for OpenAI provider (eval A/B).
    """
    from decime_api.config import settings

    cases = load_cases(version=dataset_version, suites=suites)
    llm = _build_llm(provider, model=model)
    extractor = _build_extractor(provider)
    results: list[dict[str, Any]] = []

    for case in cases:
        suite = case.get("suite") or ""
        started = time.perf_counter()
        row: dict[str, Any] = {
            "id": case.get("id"),
            "suite": suite,
            "dataset_file": case.get("_dataset_file"),
        }
        try:
            # compose_* = smoke/legacy; ru_esuy_* = pilot judge dataset (translate_to_esuy)
            if suite.startswith(("compose_", "ru_esuy_")):
                payload = dict(case["input"])
                raw_ctx = payload.pop("context", {}) or {}
                payload.pop("incoming_text", None)  # legacy datasets
                payload.pop("output_options", None)
                ctx = {
                    k: v
                    for k, v in raw_ctx.items()
                    if k in ("target_locale", "channel", "user_level")
                }
                if ctx.get("channel") not in (None, "whatsapp_text", "in_person"):
                    ctx["channel"] = "whatsapp_text"
                request = TranslateToEsRequest(
                    **payload,
                    context=ReplyContext(**ctx) if ctx else ReplyContext(),
                )
                bundle = await llm.translate_to_esuy(request)
                checks = evaluate_translate_case(bundle, case.get("expect") or {})
                row["output"] = {
                    "recommended_reply": bundle.recommended_reply,
                    "dialect_stamp": bundle.dialect_stamp,
                }
                row["usage"] = getattr(llm, "last_usage", None)
                row["deterministic"] = {**summarize_checks(checks), "checks": checks}
                if judge:
                    from decime_api.evals.judge import llm_judge_translate

                    if not settings.openai_api_key:
                        raise ValueError("OPENAI_API_KEY required for --judge")
                    row["judge"] = await llm_judge_translate(
                        source_text=request.source_text,
                        recommended_reply=bundle.recommended_reply,
                        api_key=settings.openai_api_key,
                        model=judge_model,
                    )
            elif suite.startswith(("understand_", "esuy_ru_")):
                payload = dict(case["input"])
                channel = payload.get("channel")
                if channel not in (None, "whatsapp_text", "in_person"):
                    payload["channel"] = "whatsapp_text"
                request = UnderstandTextRequest(**payload)
                understood = await llm.understand_incoming(request)
                checks = evaluate_understand_case(understood, case.get("expect") or {})
                row["output"] = {
                    "translation_ru": understood.translation_ru,
                    "translation_en": understood.translation_en,
                }
                row["usage"] = getattr(llm, "last_usage", None)
                row["deterministic"] = {**summarize_checks(checks), "checks": checks}
            elif suite.startswith("extract_"):
                request = ExtractCandidatesRequest(**case["input"])
                bundle = await extractor.extract_candidates(request)
                checks = evaluate_extract_case(bundle, case.get("expect") or {})
                row["output"] = {
                    "candidate_count": len(bundle.candidates),
                    "surfaces": [c.surface_text for c in bundle.candidates],
                }
                row["deterministic"] = {**summarize_checks(checks), "checks": checks}
            else:
                raise ValueError(f"Unknown suite: {suite}")
        except Exception as exc:  # noqa: BLE001 — collect per-case errors into report
            row["error"] = str(exc)
            row["deterministic"] = {
                "passed": False,
                "passed_checks": 0,
                "total_checks": 0,
                "failed": ["exception"],
                "checks": [],
            }
        row["latency_ms"] = int((time.perf_counter() - started) * 1000)
        results.append(row)

    meta = {
        "dataset_version": dataset_version,
        "provider": provider,
        "orchestrator": settings.llm_orchestrator,
        "model": getattr(llm, "model_name", None),
        "model_override": model,
        "suites": suites or "all",
        "judge_enabled": judge,
        "prompt": _prompt_meta_for_eval(),
    }
    summary = build_summary(results, meta)
    out = output_dir or (Path(__file__).resolve().parents[3] / "evals" / "reports")
    stem = report_stem or f"eval-{dataset_version}-{provider}-{settings.llm_orchestrator}"
    json_path, md_path = write_report(summary, out, stem)
    summary["report_json"] = str(json_path)
    summary["report_md"] = str(md_path)
    return summary
