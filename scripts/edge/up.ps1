# Start Decime edge STT/TTS and wait until fully ready (Ollama + Whisper + Orpheus).
# Usage (from repo root):
#   .\scripts\edge\up.ps1
#   ./scripts/edge/up.sh

param(
  [string]$Model = "small",
  [int]$WhisperPort = 8090,
  [int]$OrpheusPort = 5005,
  [string]$Device = "cpu",
  [string]$OrpheusDir = $env:ORPHEUS_DIR,
  [int]$TimeoutSec = 600,
  [switch]$NoWarm
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$EdgeDir = Join-Path $Root "scripts\edge"
$RunDir = Join-Path $EdgeDir ".run"
$StatePath = Join-Path $RunDir "state.json"
$LogDir = Join-Path $RunDir "logs"

New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null

function Test-HttpOk([string]$Url, [int]$Timeout = 3) {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $Timeout
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  } catch {
    return $false
  }
}

function Wait-Url([string]$Name, [string]$Url, [int]$TimeoutSec, [scriptblock]$OkCheck = $null) {
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    $ok = $false
    if ($OkCheck) {
      try { $ok = & $OkCheck } catch { $ok = $false }
    } else {
      $ok = Test-HttpOk $Url
    }
    if ($ok) {
      Write-Host "  $Name ready" -ForegroundColor Green
      return
    }
    Write-Host "  waiting $Name ..."
    Start-Sleep -Seconds 2
  }
  throw "$Name not ready within ${TimeoutSec}s ($Url)"
}

function Get-ListeningPids([int[]]$Ports) {
  $pids = @()
  foreach ($port in $Ports) {
    try {
      $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
      foreach ($conn in $conns) {
        if ($conn.OwningProcess) { $pids += [int]$conn.OwningProcess }
      }
    } catch {}
  }
  return @($pids | Select-Object -Unique)
}

function Save-State($state) {
  ($state | ConvertTo-Json -Depth 5) | Set-Content -Path $StatePath -Encoding utf8
}

function Find-OllamaExe {
  $candidates = @(
    (Get-Command ollama -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe",
    "C:\Program Files\Ollama\ollama.exe"
  ) | Where-Object { $_ -and (Test-Path $_) }
  return $candidates | Select-Object -First 1
}

Write-Host "=== Decime edge speech UP ===" -ForegroundColor Cyan

if (-not $OrpheusDir) {
  throw "Set ORPHEUS_DIR to your Orpheus-FastAPI clone path. See docs/orpheus_tts_setup.md"
}
if (-not (Test-Path $OrpheusDir)) {
  throw "Orpheus-FastAPI not found at $OrpheusDir. Set ORPHEUS_DIR or clone it."
}

$env:OLLAMA_HOST = "0.0.0.0"
$orpheusModel = "sematre/orpheus:it_es"

# --- Ollama ---
$ollamaExe = Find-OllamaExe
if (-not $ollamaExe) {
  throw "ollama not found. Install from https://ollama.com/download"
}

if (-not (Test-HttpOk "http://127.0.0.1:11434/api/tags" 2)) {
  Write-Host "Starting Ollama..."
  if ($ollamaExe -like "*ollama app.exe") {
    Start-Process -FilePath $ollamaExe | Out-Null
  } else {
    Start-Process -FilePath $ollamaExe -ArgumentList @("serve") -WindowStyle Minimized | Out-Null
  }
  Wait-Url "Ollama" "http://127.0.0.1:11434/api/tags" ([Math]::Min(120, $TimeoutSec))
} else {
  Write-Host "  Ollama already up" -ForegroundColor Green
}

Write-Host "Checking model $orpheusModel ..."
$list = & ollama list 2>&1 | Out-String
if ($list -notmatch [regex]::Escape("sematre/orpheus")) {
  Write-Host "Pulling $orpheusModel (first time can take a while)..."
  & ollama pull $orpheusModel
  if ($LASTEXITCODE -ne 0) { throw "ollama pull failed" }
} else {
  Write-Host "  model present" -ForegroundColor Green
}

# --- Orpheus ---
$orpheusAlready = Test-HttpOk "http://127.0.0.1:$OrpheusPort/docs" 2
$whisperAlready = Test-HttpOk "http://127.0.0.1:$WhisperPort/health" 2

$orpheusPid = $null
$whisperPid = $null

if (-not $orpheusAlready) {
  Write-Host "Starting Orpheus on :$OrpheusPort ..."
  $orpheusLog = Join-Path $LogDir "orpheus.out.log"
  $orpheusErr = Join-Path $LogDir "orpheus.err.log"
  $orpheusCmd = @"
`$ErrorActionPreference='Stop'
chcp 65001 > `$null
`$env:OLLAMA_HOST='0.0.0.0'
`$env:ORPHEUS_HOST='0.0.0.0'
`$env:ORPHEUS_PORT='$OrpheusPort'
`$env:PYTHONIOENCODING='utf-8'
`$env:PYTHONUTF8='1'
`$env:ORPHEUS_API_URL='http://127.0.0.1:11434/v1/completions'
`$env:ORPHEUS_MODEL_NAME='$orpheusModel'
`$env:ORPHEUS_OLLAMA_RAW='true'
Set-Location '$OrpheusDir'
& '$(Join-Path $OrpheusDir ".venv\Scripts\python.exe")' app.py
"@
  $orpheusProc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $orpheusCmd
  ) -PassThru -WindowStyle Minimized -RedirectStandardOutput $orpheusLog -RedirectStandardError $orpheusErr
  $orpheusPid = $orpheusProc.Id
} else {
  Write-Host "  Orpheus already up" -ForegroundColor Green
  $orpheusPid = (Get-ListeningPids @($OrpheusPort) | Select-Object -First 1)
}

if (-not $whisperAlready) {
  Write-Host "Starting Whisper on :$WhisperPort (model=$Model device=$Device) ..."
  $whisperLog = Join-Path $LogDir "whisper.out.log"
  $whisperErr = Join-Path $LogDir "whisper.err.log"
  $venvPy = Join-Path $Root ".venv-edge\Scripts\python.exe"
  if (-not (Test-Path $venvPy)) {
    Write-Host "Creating .venv-edge ..."
    py -3.11 -m venv (Join-Path $Root ".venv-edge")
    & $venvPy -m pip install -U pip
    & $venvPy -m pip install fastapi uvicorn python-multipart faster-whisper
  }
  $whisperProc = Start-Process -FilePath $venvPy -ArgumentList @(
    (Join-Path $EdgeDir "whisper_server.py"),
    "--host", "0.0.0.0",
    "--port", "$WhisperPort",
    "--model", $Model,
    "--device", $Device
  ) -PassThru -WindowStyle Minimized -RedirectStandardOutput $whisperLog -RedirectStandardError $whisperErr
  $whisperPid = $whisperProc.Id
} else {
  Write-Host "  Whisper already up" -ForegroundColor Green
  $whisperPid = (Get-ListeningPids @($WhisperPort) | Select-Object -First 1)
}

Save-State @{
  started_at = (Get-Date).ToString("o")
  whisper_port = $WhisperPort
  orpheus_port = $OrpheusPort
  whisper_pid = $whisperPid
  orpheus_pid = $orpheusPid
  model = $Model
  device = $Device
}

# --- Wait ready ---
Write-Host "Waiting until services are ready (timeout ${TimeoutSec}s)..."
Wait-Url "Whisper" "http://127.0.0.1:$WhisperPort/health" $TimeoutSec {
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:$WhisperPort/health" -TimeoutSec 3
    return ($h.status -eq "ok")
  } catch { return $false }
}
Wait-Url "Orpheus" "http://127.0.0.1:$OrpheusPort/docs" $TimeoutSec

if (-not $NoWarm) {
  Write-Host "Warming Orpheus model in Ollama (keep_alive=-1)..."
  try {
    $warm = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/api/generate" -TimeoutSec ([Math]::Max(120, [Math]::Min(300, $TimeoutSec))) -ContentType "application/json" -Body (@{
      model = $orpheusModel
      prompt = " "
      stream = $false
      keep_alive = -1
    } | ConvertTo-Json)
    Write-Host "  Ollama model warm done" -ForegroundColor Green
  } catch {
    Write-Host "  warm warning: $($_.Exception.Message)" -ForegroundColor Yellow
  }
}

$tsIp = $null
$tsHint = $null
if (Get-Command tailscale -ErrorAction SilentlyContinue) {
  # tailscale writes "no current Tailscale IPs; state: NoState" to stderr when
  # logged out / starting - swallow so UP still looks clean.
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "SilentlyContinue"
  try {
    $ipLines = & tailscale ip -4 2>$null
    if ($LASTEXITCODE -eq 0 -and $ipLines) {
      $tsIp = (($ipLines | Select-Object -First 1) -as [string]).Trim()
      if (-not ($tsIp -match '^100\.')) { $tsIp = $null }
    }
    if (-not $tsIp) {
      $st = (& tailscale status --json 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue)
      $backend = $st.BackendState
      if ($backend -and $backend -ne "Running") {
        $tsHint = "Tailscale state=$backend - run: tailscale up  (needed for VM EDGE_SPEECH_HOST)"
      } else {
        $tsHint = "Tailscale has no 100.x IP yet - run: tailscale up"
      }
    }
  } catch {
    $tsHint = "Tailscale IP unavailable - run: tailscale up"
  } finally {
    $ErrorActionPreference = $prevEap
  }
}

Write-Host ""
Write-Host "Edge speech READY" -ForegroundColor Green
Write-Host "  STT  http://127.0.0.1:$WhisperPort/health"
Write-Host "  TTS  http://127.0.0.1:$OrpheusPort/docs"
Write-Host "  Ollama http://127.0.0.1:11434/api/tags"
if ($tsIp) {
  Write-Host "  Tailscale $tsIp  (EDGE_SPEECH_HOST=$tsIp)"
} elseif ($tsHint) {
  Write-Host "  $tsHint" -ForegroundColor Yellow
}
Write-Host "Stop with: .\scripts\edge\down.ps1"
