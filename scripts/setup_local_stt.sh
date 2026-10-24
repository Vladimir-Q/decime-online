#!/usr/bin/env bash
# Local STT setup for Decime UY (OpenAI Whisper via faster-whisper).
# karanchopda333/whisper on Ollama is text-only Llama — not used for ASR in this project.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/apps/api"
MODEL_SIZE="${WHISPER_MODEL_SIZE:-base}"

echo "=== Decime UY — local STT (Whisper) ==="

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARN: ffmpeg not in PATH — install it for broad audio format support."
else
  echo "ffmpeg: OK"
fi

cd "$API"
if [[ ! -d .venv ]]; then
  py -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

pip install -q -e ".[local-stt,dev]"
echo "Downloading Whisper weights ($MODEL_SIZE) ..."
python -c "
from faster_whisper import WhisperModel
WhisperModel('$MODEL_SIZE', device='cpu', compute_type='int8')
print('Whisper model ready:', '$MODEL_SIZE')
"

echo ""
echo "Done. In .env:"
echo "  STT_PROVIDER=faster_whisper"
echo "  WHISPER_MODEL_SIZE=$MODEL_SIZE"
echo "  LLM_PROVIDER=openai"
echo "  TTS_PROVIDER=openai"
