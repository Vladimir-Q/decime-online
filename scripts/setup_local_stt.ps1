# Local STT setup for Decime UY (OpenAI Whisper via faster-whisper).
# Note: karanchopda333/whisper on Ollama is a text-only Llama model, not speech-to-text.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ApiDir = Join-Path $RepoRoot "apps\api"

Write-Host "=== Decime UY — local STT (Whisper) ===" -ForegroundColor Cyan

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "ffmpeg not found in PATH. Install it (e.g. winget install Gyan.FFmpeg) — Whisper needs it for many audio formats."
} else {
    Write-Host "ffmpeg: OK"
}

$VenvPython = Join-Path $ApiDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python venv in apps/api ..."
    Push-Location $ApiDir
    py -m venv .venv
    Pop-Location
}

Write-Host "Installing API + local-stt extras ..."
Push-Location $ApiDir
& $VenvPython -m pip install -q -e ".[local-stt,dev]"

$ModelSize = $env:WHISPER_MODEL_SIZE
if (-not $ModelSize) { $ModelSize = "base" }

Write-Host "Downloading Whisper weights ($ModelSize) — first run only, may take a few minutes ..."
& $VenvPython -c @"
from faster_whisper import WhisperModel
WhisperModel('$ModelSize', device='cpu', compute_type='int8')
print('Whisper model ready:', '$ModelSize')
"@

Pop-Location

Write-Host ""
Write-Host "Done. In .env set:" -ForegroundColor Green
Write-Host "  STT_PROVIDER=faster_whisper"
Write-Host "  WHISPER_MODEL_SIZE=$ModelSize"
Write-Host "  LLM_PROVIDER=openai"
Write-Host "  TTS_PROVIDER=openai"
Write-Host ""
Write-Host "Start API: cd apps/api; .\.venv\Scripts\activate; uvicorn decime_api.main:app --reload --app-dir src"
