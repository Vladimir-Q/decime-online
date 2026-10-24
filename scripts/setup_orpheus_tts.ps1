# Pull Orpheus Spanish/Italian model for Ollama (used by Orpheus-FastAPI backend).
$ErrorActionPreference = "Stop"

Write-Host "=== Orpheus TTS setup ===" -ForegroundColor Cyan
Write-Host "Pulling sematre/orpheus:it_es into Ollama..."
ollama pull sematre/orpheus:it_es

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Install Orpheus-FastAPI (Python 3.10/3.11) — see docs/orpheus_tts_setup.md"
Write-Host "2. Set ORPHEUS_API_URL=http://localhost:11434/v1/completions"
Write-Host "3. Set ORPHEUS_MODEL_NAME=sematre/orpheus:it_es"
Write-Host "4. Run: python app.py  (port 5005)"
Write-Host "5. In Decime .env: TTS_PROVIDER=orpheus"
