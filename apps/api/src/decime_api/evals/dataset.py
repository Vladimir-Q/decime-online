"""Load versioned JSONL evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# apps/api/src/decime_api/evals/dataset.py → apps/api/evals/datasets
_DATASETS_ROOT = Path(__file__).resolve().parents[3] / "evals" / "datasets"


def datasets_root() -> Path:
    return _DATASETS_ROOT


def list_suite_files(version: str = "v1") -> list[Path]:
    folder = _DATASETS_ROOT / version
    if not folder.is_dir():
        raise FileNotFoundError(f"Dataset version not found: {folder}")
    return sorted(folder.glob("*.jsonl"))


def load_cases(
    *,
    version: str = "v1",
    suites: list[str] | None = None,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in list_suite_files(version):
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                text = line.strip()
                if not text or text.startswith("#"):
                    continue
                try:
                    case = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL {path.name}:{line_no}") from exc
                if suites and case.get("suite") not in suites:
                    continue
                case["_dataset_file"] = path.name
                case["_dataset_version"] = version
                cases.append(case)
    return cases
