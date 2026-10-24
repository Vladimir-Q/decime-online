"""Unit tests for Experiment 2 structured judge (no paid API)."""

from __future__ import annotations

from decime_api.evals.judge_pilot import normalize_judge_payload
from decime_api.services.ai.llm_json_schemas import judge_translate_pilot_json_schema


def test_judge_schema_required_fields() -> None:
    schema = judge_translate_pilot_json_schema()
    required = set(schema["required"])
    assert required == {
        "semantic_fidelity",
        "uy_naturalness",
        "style_preservation",
        "no_additions_omissions",
        "critical_error",
        "rationale",
        "error_category",
    }
    for key in (
        "semantic_fidelity",
        "uy_naturalness",
        "style_preservation",
        "no_additions_omissions",
    ):
        prop = schema["properties"][key]
        assert prop["minimum"] == 1
        assert prop["maximum"] == 5


def test_normalize_judge_payload_clamps_and_defaults() -> None:
    out = normalize_judge_payload(
        {
            "semantic_fidelity": 9,
            "uy_naturalness": 0,
            "style_preservation": "3",
            "no_additions_omissions": 4,
            "critical_error": 1,
            "rationale": "  Mild omission of hedge.  ",
            "error_category": "OMISSION",
        }
    )
    assert out["semantic_fidelity"] == 5
    assert out["uy_naturalness"] == 1
    assert out["style_preservation"] == 3
    assert out["no_additions_omissions"] == 4
    assert out["critical_error"] is True
    assert out["rationale"] == "Mild omission of hedge."
    assert out["error_category"] == "omission"


def test_normalize_judge_payload_unknown_category() -> None:
    out = normalize_judge_payload({"error_category": "not-a-label"})
    assert out["error_category"] == "other"
    assert out["semantic_fidelity"] == 1
