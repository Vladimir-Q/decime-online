"""Unit tests for Stage 4 A/B case_id pair integrity."""

from __future__ import annotations

from types import SimpleNamespace

from decime_api.evals.pair_integrity import (
    check_langsmith_chronology,
    check_local_pair,
    chronological_case_ids,
    index_report_cases,
)


def _report(rows: list[dict]) -> dict:
    return {"cases": rows}


def test_index_report_cases() -> None:
    by_id = index_report_cases(
        _report(
            [
                {"id": "human-es-01", "output": {"translation_ru": "а"}},
                {"id": "human-es-01", "output": {"translation_ru": "dup"}},
            ]
        )
    )
    assert list(by_id) == ["human-es-01"]
    assert by_id["human-es-01"]["output"]["translation_ru"] == "а"


def test_check_local_pair_ok() -> None:
    a = _report(
        [
            {"id": "c1", "output": {"translation_ru": "раз"}},
            {"id": "c2", "output": {"translation_ru": "два"}},
        ]
    )
    b = _report(
        [
            {"id": "c2", "output": {"translation_ru": "dos"}},
            {"id": "c1", "output": {"translation_ru": "uno"}},
        ]
    )
    summary = check_local_pair(
        report_a=a,
        report_b=b,
        dataset_cases=[
            {"id": "c1", "input": {"source_text": "hola"}},
            {"id": "c2", "input": {"source_text": "chau"}},
        ],
    )
    assert summary["ok"] is True
    assert summary["shared_case_count"] == 2
    assert summary["failed_pairs"] == []


def test_check_local_pair_missing_and_empty() -> None:
    a = _report([{"id": "c1", "output": {"translation_ru": "раз"}}, {"id": "c2", "output": {}}])
    b = _report([{"id": "c1", "output": {"translation_ru": "uno"}}])
    summary = check_local_pair(report_a=a, report_b=b)
    assert summary["ok"] is False
    assert "c2" in summary["only_in_a"]
    failed = {p["case_id"]: p["issues"] for p in summary["pairs"]}
    assert "missing_in_B" in failed["c2"]
    assert "empty_output_A" in failed["c2"] or "missing_in_B" in failed["c2"]


def test_chronological_case_ids_and_paq_order() -> None:
    runs_a = [
        SimpleNamespace(
            start_time=2,
            metadata={},
            outputs={"case_id": "c2"},
            inputs={},
        ),
        SimpleNamespace(
            start_time=1,
            metadata={"decime_case_id": "c1"},
            outputs={},
            inputs={},
        ),
    ]
    seq = chronological_case_ids(runs_a)
    assert seq == ["c1", "c2"]

    good = check_langsmith_chronology(case_ids_a=["c1", "c2"], case_ids_b=["c1", "c2"])
    assert good["ok"] is True

    bad = check_langsmith_chronology(case_ids_a=["c1", "c2"], case_ids_b=["c2", "c1"])
    assert bad["ok"] is False
    assert bad["order_mismatches"][0]["case_id_a"] == "c1"
    assert bad["order_mismatches"][0]["case_id_b"] == "c2"
