#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Decime UY dev check =="

echo "-- Backend tests --"
cd "$ROOT/apps/api"
python -m pytest
python -m ruff check src

echo "-- Backend health (requires running server) --"
curl -sf http://localhost:8000/health | python -m json.tool

echo "-- Frontend lint --"
cd "$ROOT/apps/web"
npm run lint

echo "All checks passed."
