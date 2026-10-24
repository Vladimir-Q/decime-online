"""Stage 6: evaluation dataset + deterministic metrics (no paid APIs)."""

from __future__ import annotations

import pytest

from decime_api.evals.dataset import load_cases
from decime_api.evals.deterministic import evaluate_translate_case, summarize_checks
from decime_api.evals.runner import run_evaluation
from decime_api.schemas.compose import ReplyBundle


def test_load_v1_datasets() -> None:
    cases = load_cases(version="v1")
    assert len(cases) >= 8
    suites = {c["suite"] for c in cases}
    assert "compose_ru_esuy" in suites
    assert "understand_esuy_ru" in suites
    assert "extract_lexicon" in suites


def test_compose_deterministic_checks() -> None:
    bundle = ReplyBundle(
        target_locale="es-UY-montevideo",
        dialect_stamp="es-UY · Montevideo",
        source_language="ru",
        intent_summary_ru="x",
        recommended_reply="¿Se puede pagar con tarjeta?",
    )
    checks = evaluate_translate_case(
        bundle,
        {
            "must_contain_any": ["tarjeta"],
            "forbid_cyrillic_in_reply": True,
            "min_reply_chars": 5,
        },
    )
    summary = summarize_checks(checks)
    assert summary["passed"] is True


def test_compose_deterministic_fails_on_cyrillic() -> None:
    bundle = ReplyBundle(
        target_locale="es-UY-montevideo",
        dialect_stamp="es-UY",
        source_language="ru",
        intent_summary_ru="x",
        recommended_reply="Можно оплатить картой",
    )
    checks = evaluate_translate_case(bundle, {"forbid_cyrillic_in_reply": True})
    assert any(not c["passed"] and c["name"] == "forbid_cyrillic_in_reply" for c in checks)


@pytest.mark.asyncio
async def test_run_evaluation_fake_all_pass(tmp_path) -> None:
    # Smoke suites only — extended compose_ru_esuy_30 is for live model A/B, not Fake.
    summary = await run_evaluation(
        provider="fake",
        dataset_version="v1",
        suites=[
            "compose_ru_esuy",
            "compose_en_esuy",
            "understand_esuy_ru",
            "understand_esuy_en",
            "extract_lexicon",
        ],
        judge=False,
        output_dir=tmp_path,
        report_stem="unit-fake",
    )
    assert summary["meta"]["case_count"] >= 8
    assert summary["measured"]["deterministic_pass_rate"] == 1.0
    assert summary["measured"]["error_count"] == 0
    assert (tmp_path / "unit-fake.md").is_file()
    cases = summary.get("cases") or []
    text_cases = [c for c in cases if c.get("suite", "").startswith(("compose_", "understand_"))]
    assert text_cases
    assert all("usage" in c for c in text_cases)
    assert all(c["usage"]["model"] == "fake-compose-v1" for c in text_cases)
