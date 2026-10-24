"""Round-trip tests for eval dataset Excel conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("openpyxl")

from decime_api.evals.dataset_xlsx import (
    cases_from_jsonl,
    export_jsonl_to_xlsx,
    flatten_case,
    import_xlsx_to_jsonl,
    unflatten_row,
)


def test_flatten_unflatten_compose_case() -> None:
    case = {
        "id": "compose-ru-card-01",
        "suite": "compose_ru_esuy_30",
        "input": {
            "source_language": "ru",
            "source_text": "Можно оплатить картой?",
            "context": {"channel": "whatsapp_text", "user_level": "A2"},
        },
        "expect": {
            "must_contain_any": ["tarjeta", "pagar"],
            "forbid_cyrillic_in_reply": True,
            "min_reply_chars": 8,
        },
    }
    flat = flatten_case(case)
    assert flat["expect.must_contain_any"] == "tarjeta | pagar"
    rebuilt = unflatten_row(flat)
    assert rebuilt["id"] == case["id"]
    assert rebuilt["suite"] == case["suite"]
    assert rebuilt["input"]["context"]["user_level"] == "A2"
    assert "tone" not in rebuilt["input"]["context"]
    assert rebuilt["expect"]["must_contain_any"] == ["tarjeta", "pagar"]
    assert rebuilt["expect"]["forbid_cyrillic_in_reply"] is True
    assert rebuilt["expect"]["min_reply_chars"] == 8


def test_xlsx_roundtrip_compose30(tmp_path: Path) -> None:
    src = (
        Path(__file__).resolve().parents[3]
        / "evals"
        / "datasets"
        / "v1"
        / "compose_ru_esuy_30.jsonl"
    )
    if not src.is_file():
        pytest.skip("compose_ru_esuy_30.jsonl not present")

    original = cases_from_jsonl(src)
    xlsx = tmp_path / "out.xlsx"
    out_jsonl = tmp_path / "out.jsonl"
    assert export_jsonl_to_xlsx(src, xlsx) == len(original)
    assert import_xlsx_to_jsonl(xlsx, out_jsonl) == len(original)
    restored = cases_from_jsonl(out_jsonl)
    assert len(restored) == len(original)
    for a, b in zip(original, restored, strict=True):
        assert a["id"] == b["id"]
        assert a["suite"] == b["suite"]
        assert a["input"] == b["input"]
        assert a["expect"] == b["expect"]
