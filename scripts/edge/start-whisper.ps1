# Start OpenAI-compatible Whisper for Decime edge (Tailscale).
# Usage: .\scripts\edge\start-whisper.ps1 [-Model small] [-Port 8090]

param(
  [string]$Model = "small",
  [int]$Port = 8090,
  [string]$HostAddress = "0.0.0.0",
  [ValidateSet("auto", "cpu", "cuda")]
  [string]$Device = "auto"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

$venv = Join-Path $Root ".venv-edge"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
  Write-Host "Creating .venv-edge …"
  py -3.11 -m venv $venv
  & "$venv\Scripts\python.exe" -m pip install -U pip
  & "$venv\Scripts\python.exe" -m pip install fastapi uvicorn python-multipart faster-whisper
}

Write-Host "Whisper edge server on http://${HostAddress}:$Port (model=$Model device=$Device)"
Write-Host "Allow Windows Firewall for TCP $Port (Tailscale / Private)."
& "$venv\Scripts\python.exe" (Join-Path $Root "scripts\edge\whisper_server.py") `
  --host $HostAddress --port $Port --model $Model --device $Device
