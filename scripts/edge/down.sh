#!/usr/bin/env bash
# Stop edge STT/TTS and Ollama completely.
# Usage from repo root: ./scripts/edge/down.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v powershell.exe >/dev/null 2>&1; then
  exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/down.ps1" "$@"
fi
if command -v pwsh >/dev/null 2>&1; then
  exec pwsh -NoProfile -File "$SCRIPT_DIR/down.ps1" "$@"
fi
echo "PowerShell is required to run edge speech on this machine." >&2
exit 1
