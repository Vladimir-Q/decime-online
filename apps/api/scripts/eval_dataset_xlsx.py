#!/usr/bin/env python3
"""Convert Decime eval JSONL datasets to Excel and back.

Requires: pip install openpyxl   (or: pip install -e ".[dev]")

Examples (from apps/api):

  # JSONL -> Excel (edit in Excel / LibreOffice / Google Sheets)
  python scripts/eval_dataset_xlsx.py export \\
    evals/datasets/v1/compose_ru_esuy_30.jsonl \\
    evals/datasets/v1/compose_ru_esuy_30.xlsx

  # Excel -> JSONL (after manual edits)
  python scripts/eval_dataset_xlsx.py import \\
    evals/datasets/v1/compose_ru_esuy_30.xlsx \\
    evals/datasets/v1/compose_ru_esuy_30.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _main() -> int:
    parser = argparse.ArgumentParser(description="Eval dataset JSONL <-> Excel (.xlsx)")
    sub = parser.add_subparsers(dest="command", required=True)

    export_p = sub.add_parser("export", help="JSONL -> .xlsx")
    export_p.add_argument("jsonl", type=Path)
    export_p.add_argument("xlsx", type=Path)

    import_p = sub.add_parser("import", help=".xlsx -> JSONL")
    import_p.add_argument("xlsx", type=Path)
    import_p.add_argument("jsonl", type=Path)

    args = parser.parse_args()

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("Missing dependency: pip install openpyxl", file=sys.stderr)
        return 2

    from decime_api.evals.dataset_xlsx import export_jsonl_to_xlsx, import_xlsx_to_jsonl

    if args.command == "export":
        if not args.jsonl.is_file():
            print(f"Not found: {args.jsonl}", file=sys.stderr)
            return 1
        n = export_jsonl_to_xlsx(args.jsonl, args.xlsx)
        print(f"Exported {n} cases -> {args.xlsx}")
        return 0

    if args.command == "import":
        if not args.xlsx.is_file():
            print(f"Not found: {args.xlsx}", file=sys.stderr)
            return 1
        n = import_xlsx_to_jsonl(args.xlsx, args.jsonl)
        print(f"Imported {n} cases -> {args.jsonl}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
