#!/usr/bin/env python3
"""Emit JSON patch for VM .env (run locally; pipe to VM updater)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
local: dict[str, str] = {}
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        local[k.strip()] = v.strip()

key = local.get("OPENAI_API_KEY", "")
if not key:
    sys.exit("OPENAI_API_KEY missing in repo .env")

patch = {
    "LLM_PROVIDER": "openai",
    "OPENAI_API_KEY": key,
    "OPENAI_TEXT_MODEL": local.get("OPENAI_TEXT_MODEL", "gpt-6-luna"),
}
sys.stdout.write(json.dumps(patch))
