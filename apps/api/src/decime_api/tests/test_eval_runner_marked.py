"""Eval-tier tests marked ``eval`` (excluded from default ``pytest`` / free CI).

Fake path remains covered in ``test_evals_stage6.py`` (unmarked, free).
This module is for explicit ``pytest -m eval`` and optional paid runs.

  pytest -m eval
  DECIME_RUN_EVAL=1 OPENAI_API_KEY=... pytest -m eval -k openai_compose
"""

from __future__ import annotations

import os

import pytest

from decime_api.evals.runner import run_evaluation

pytestmark = pytest.mark.eval


@pytest.mark.asyncio
async def test_eval_marker_smoke_fake(tmp_path) -> None:
    """Sanity check when someone runs ``pytest -m eval`` without API keys."""
    summary = await run_evaluation(
        provider="fake",
        dataset_version="v1",
        suites=["compose_ru_esuy"],
        judge=False,
        output_dir=tmp_path,
        report_stem="marker-fake-compose",
    )
    assert summary["measured"]["deterministic_pass_rate"] == 1.0
    assert summary["measured"]["error_count"] == 0


@pytest.mark.asyncio
async def test_eval_openai_compose_optional(tmp_path) -> None:
    if os.environ.get("DECIME_RUN_EVAL", "").strip() not in {"1", "true", "yes"}:
        pytest.skip("Set DECIME_RUN_EVAL=1 to run paid OpenAI eval suite")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY required")

    summary = await run_evaluation(
        provider="openai",
        dataset_version="v1",
        suites=["compose_ru_esuy"],
        judge=False,
        output_dir=tmp_path,
        report_stem="ci-openai-compose",
    )
    assert summary["meta"]["case_count"] >= 1
    assert summary["measured"]["error_count"] == 0
