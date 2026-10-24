#!/usr/bin/env bash
# Decime UY — local dev (Git Bash on Windows). Open 4 tabs and run one block each.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

check() {
  local name="$1"
  local url="$2"
  if curl -sf --max-time 2 "$url" >/dev/null 2>&1; then
    echo "  OK  $name — $url"
  else
    echo "  --  $name — not running ($url)"
  fi
}

echo "=== Decime UY local stack (Git Bash) ==="
echo ""
echo "Your .env (typical): LLM=openai (cloud), STT=faster_whisper (in API), TTS=orpheus."
echo ""
echo "--- Tab 1: Ollama (for Orpheus TTS; wake daemon) ---"
echo "ollama list"
echo ""
echo "--- Tab 2: Orpheus TTS :5005 ---"
echo "export PYTHONIOENCODING=utf-8 PYTHONUTF8=1"
echo 'cd "$ORPHEUS_DIR" && source .venv/Scripts/activate && python app.py'
echo ""
echo "--- Tab 3: API :8000 ---"
echo "cd $ROOT/apps/api && source .venv/Scripts/activate"
echo "uvicorn decime_api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000"
echo ""
echo "--- Tab 4: Web :3000 ---"
echo "cd $ROOT/apps/web && npm run dev"
echo ""
echo "Browser: http://localhost:3000/app/quick-reply/"
echo ""
echo "--- Status now ---"
check "Ollama" "http://127.0.0.1:11434/api/tags"
check "Orpheus" "http://127.0.0.1:5005/health"
check "API" "http://127.0.0.1:8000/health"
check "Web" "http://127.0.0.1:3000"
