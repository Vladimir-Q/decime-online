#!/usr/bin/env python3
"""Apply JSON env patch from stdin to deploy/.env in cwd."""
import json
import sys
from pathlib import Path

updates = json.load(sys.stdin)
p = Path(".env")
lines = p.read_text(encoding="utf-8").splitlines()
out: list[str] = []
seen: set[str] = set()
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        k = line.split("=", 1)[0]
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("updated", sorted(updates.keys()))
