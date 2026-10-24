# Stop Decime edge STT/TTS completely (Whisper, Orpheus, and Ollama).
# Usage (from repo root):
#   .\scripts\edge\down.ps1
#   ./scripts/edge/down.sh

param(
  [int]$WhisperPort = 8090,
  [int]$OrpheusPort = 5005,
  [switch]$KeepOllama
)

$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RunDir = Join-Path $Root "scripts\edge\.run"
$StatePath = Join-Path $RunDir "state.json"

Write-Host "=== Decime edge speech DOWN ===" -ForegroundColor Cyan

function Stop-Tree([int]$ProcessId) {
  if ($ProcessId -le 0) { return }
  try {
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
      Stop-Tree ([int]$child.ProcessId)
    }
  } catch {}
  try {
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  } catch {}
}

function Stop-PortListeners([int[]]$Ports) {
  foreach ($port in $Ports) {
    try {
      $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
      foreach ($conn in $conns) {
        if ($conn.OwningProcess) {
          Write-Host "  kill pid $($conn.OwningProcess) on :$port"
          Stop-Tree ([int]$conn.OwningProcess)
        }
      }
    } catch {}
  }
}

function Stop-OllamaAll {
  Write-Host "Stopping Ollama..."
  # Prefer graceful CLI if available
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    try { & ollama stop sematre/orpheus:it_es 2>$null | Out-Null } catch {}
  }

  $names = @("ollama", "ollama app", "Ollama")
  foreach ($name in $names) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
      Write-Host "  kill $($_.ProcessName) pid=$($_.Id)"
      Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
  }

  # Catch any remaining ollama*.exe by WMI name
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '(?i)^ollama' } |
    ForEach-Object {
      Write-Host "  kill $($_.Name) pid=$($_.ProcessId)"
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

  # Port fallback
  Stop-PortListeners @(11434)
}

# Kill tracked PIDs from last up
if (Test-Path $StatePath) {
  try {
    $state = Get-Content $StatePath -Raw | ConvertFrom-Json
    if ($state.whisper_port) { $WhisperPort = [int]$state.whisper_port }
    if ($state.orpheus_port) { $OrpheusPort = [int]$state.orpheus_port }
    if ($state.whisper_pid) {
      Write-Host "  stop tracked Whisper pid=$($state.whisper_pid)"
      Stop-Tree ([int]$state.whisper_pid)
    }
    if ($state.orpheus_pid) {
      Write-Host "  stop tracked Orpheus pid=$($state.orpheus_pid)"
      Stop-Tree ([int]$state.orpheus_pid)
    }
  } catch {
    Write-Host "  state file unreadable, falling back to ports"
  }
}

Write-Host "Stopping Whisper/Orpheus listeners..."
Stop-PortListeners @($WhisperPort, $OrpheusPort)

# Extra: edge python hosts that may still hold the ports briefly
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object {
    ($_.CommandLine -match 'whisper_server\.py') -or
    ($_.CommandLine -match 'Orpheus-FastAPI' -and $_.CommandLine -match 'app\.py')
  } |
  ForEach-Object {
    Write-Host "  kill leftover $($_.Name) pid=$($_.ProcessId)"
    Stop-Tree ([int]$_.ProcessId)
  }

if (-not $KeepOllama) {
  Stop-OllamaAll
} else {
  Write-Host "Keeping Ollama (-KeepOllama)"
}

Start-Sleep -Seconds 1

$left = @()
foreach ($port in @($WhisperPort, $OrpheusPort, 11434)) {
  if ($KeepOllama -and $port -eq 11434) { continue }
  try {
    $still = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($still) { $left += $port }
  } catch {}
}

if (Test-Path $StatePath) {
  Remove-Item $StatePath -Force -ErrorAction SilentlyContinue
}

if ($left.Count -gt 0) {
  Write-Host "Still listening on: $($left -join ', ')" -ForegroundColor Yellow
  exit 1
}

Write-Host "Edge speech STOPPED" -ForegroundColor Green
