# Decime Android QA on emulator — no physical phone required.
# Usage: .\scripts\android_qa.ps1
# Optional: -SkipBuild -SkipEmulator

param(
    [switch]$SkipBuild,
    [switch]$SkipEmulator
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $repoRoot "apps\web"
$apiVenv = Join-Path $repoRoot "apps\api\.venv\Scripts\python.exe"
$e2e = Join-Path $repoRoot "scripts\android_e2e.py"
$sdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android\Sdk" }
$adb = Join-Path $sdk "platform-tools\adb.exe"
$emulator = Join-Path $sdk "emulator\emulator.exe"

function Test-ApiHealth {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -UseBasicParsing
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-EmulatorReady {
    if (-not (Test-Path $adb)) { return $false }
    $out = & $adb devices 2>&1 | Out-String
    return $out -match "emulator-\d+\s+device"
}

Write-Host "=== Decime Android QA (emulator) ===" -ForegroundColor Cyan

if (-not (Test-Path $apiVenv)) {
    Write-Error "API venv missing: $apiVenv"
}

if (-not (Test-ApiHealth)) {
    Write-Host "Starting API on :8000..."
    Start-Process -FilePath $apiVenv -ArgumentList "-m uvicorn decime_api.main:app --app-dir src --host 0.0.0.0 --port 8000" -WorkingDirectory (Join-Path $repoRoot "apps\api") -WindowStyle Minimized
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        if (Test-ApiHealth) { break }
        Start-Sleep -Seconds 1
    }
    if (-not (Test-ApiHealth)) {
        Write-Error "API did not start on http://127.0.0.1:8000/health"
    }
    Write-Host "OK API running"
} else {
    Write-Host "OK API already running"
}

if (-not $SkipEmulator -and -not (Test-EmulatorReady)) {
    if (-not (Test-Path $emulator)) {
        Write-Error "Emulator not found: $emulator"
    }
    $avd = & $emulator -list-avds | Select-Object -First 1
    if (-not $avd) {
        Write-Error "No AVD configured. Create one in Android Studio."
    }
    Write-Host "Starting emulator: $avd"
    Start-Process -FilePath $emulator -ArgumentList "-avd $avd -no-snapshot-load -gpu swiftshader_indirect" -WindowStyle Minimized
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        if (Test-EmulatorReady) { break }
        Start-Sleep -Seconds 3
    }
    if (-not (Test-EmulatorReady)) {
        Write-Error "Emulator did not become ready"
    }
    Write-Host "OK Emulator ready"
} elseif (Test-EmulatorReady) {
    Write-Host "OK Emulator already running"
} else {
    Write-Host "SkipEmulator: expecting adb device"
}

if (-not $SkipBuild) {
    $env:JAVA_HOME = if ($env:JAVA_HOME) { $env:JAVA_HOME } else { "C:\Program Files\Android\Android Studio\jbr" }
    $env:ANDROID_HOME = $sdk
    Push-Location $webRoot
    try {
        Write-Host "Building APK..."
        npm run cap:apk
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Running E2E..."
& $apiVenv $e2e
if ($LASTEXITCODE -ne 0) {
    Write-Host "E2E FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "QA PASSED (emulator)" -ForegroundColor Green
