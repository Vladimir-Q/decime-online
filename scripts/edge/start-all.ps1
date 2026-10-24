# Compatibility wrapper — prefer: .\scripts\edge\up.ps1
param(
  [string]$Model = "small",
  [int]$WhisperPort = 8090,
  [int]$OrpheusPort = 5005,
  [string]$Device = "cpu",
  [string]$OrpheusDir = $env:ORPHEUS_DIR
)

& (Join-Path $PSScriptRoot "up.ps1") `
  -Model $Model `
  -WhisperPort $WhisperPort `
  -OrpheusPort $OrpheusPort `
  -Device $Device `
  -OrpheusDir $OrpheusDir
