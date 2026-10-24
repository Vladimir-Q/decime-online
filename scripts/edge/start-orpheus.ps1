# Start Orpheus-FastAPI for Decime edge TTS (expects Ollama already running).
# Set ORPHEUS_DIR to your Orpheus-FastAPI clone path.
# Usage: .\scripts\edge\start-orpheus.ps1

param(
  [string]$OrpheusDir = $env:ORPHEUS_DIR,
  [int]$Port = 5005
)

$ErrorActionPreference = "Stop"

if (-not $OrpheusDir) {
  Write-Error "Set ORPHEUS_DIR to your Orpheus-FastAPI clone path. See docs/orpheus_tts_setup.md"
}

if (-not (Test-Path $OrpheusDir)) {
  Write-Error "Orpheus-FastAPI not found at $OrpheusDir. Clone it and/or set ORPHEUS_DIR. See docs/orpheus_tts_setup.md"
}

# Ensure Ollama accepts Tailscale peers
if (-not $env:OLLAMA_HOST) {
  $env:OLLAMA_HOST = "0.0.0.0"
}

# Force Tailscale-reachable bind (overrides Orpheus .env if it says 127.0.0.1)
$env:ORPHEUS_HOST = "0.0.0.0"
$env:ORPHEUS_PORT = "$Port"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
if (-not $env:ORPHEUS_API_URL) {
  $env:ORPHEUS_API_URL = "http://127.0.0.1:11434/v1/completions"
}
if (-not $env:ORPHEUS_MODEL_NAME) {
  $env:ORPHEUS_MODEL_NAME = "sematre/orpheus:it_es"
}
# Ollama /v1/completions returns chat text; raw /api/generate emits audio tokens.
$env:ORPHEUS_OLLAMA_RAW = "true"

Set-Location $OrpheusDir
$py = Join-Path $OrpheusDir ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Error "Missing $py — create the venv per docs/orpheus_tts_setup.md"
}

# Patch .env so dotenv reload doesn't snap back to localhost
$envFile = Join-Path $OrpheusDir ".env"
if (Test-Path $envFile) {
  $content = Get-Content $envFile -Raw
  if ($content -match '(?m)^ORPHEUS_HOST=') {
    $content = $content -replace '(?m)^ORPHEUS_HOST=.*', 'ORPHEUS_HOST=0.0.0.0'
  } else {
    $content = $content.TrimEnd() + "`nORPHEUS_HOST=0.0.0.0`n"
  }
  if ($content -match '(?m)^ORPHEUS_OLLAMA_RAW=') {
    $content = $content -replace '(?m)^ORPHEUS_OLLAMA_RAW=.*', 'ORPHEUS_OLLAMA_RAW=true'
  } else {
    $content = $content.TrimEnd() + "`nORPHEUS_OLLAMA_RAW=true`n"
  }
  Set-Content -Path $envFile -Value $content -NoNewline
}

Write-Host "Orpheus on http://0.0.0.0:$Port (Ollama local). Allow firewall TCP $Port."
& $py app.py
