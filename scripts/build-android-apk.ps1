# Build Decime UY debug APK (Windows)
# Default: production API (https://api.decime.online)
# Use -Dev for LAN/emulator testing (no baked-in production URL)
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $repoRoot "apps\web"
$androidRoot = Join-Path $webRoot "android"
$apkPath = Join-Path $androidRoot "app\build\outputs\apk\debug\app-debug.apk"

function Set-JavaHomeFromAndroidStudio {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Android\Android Studio\jbr",
        "${env:ProgramFiles}\Android\Android Studio\jbr",
        "${env:ProgramFiles(x86)}\Android\Android Studio\jbr"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate "bin\java.exe")) {
            $env:JAVA_HOME = $candidate
            Write-Host "Using JAVA_HOME=$env:JAVA_HOME"
            return
        }
    }
}

function Set-AndroidSdk {
    $candidates = @(
        $env:ANDROID_HOME,
        $env:ANDROID_SDK_ROOT,
        (Join-Path $env:LOCALAPPDATA "Android\Sdk"),
        (Join-Path $env:USERPROFILE "AppData\Local\Android\Sdk")
    ) | Where-Object { $_ -and (Test-Path $_) }

    if ($candidates.Count -eq 0) {
        return
    }

    $sdkPath = $candidates[0]
    $env:ANDROID_HOME = $sdkPath
    $env:ANDROID_SDK_ROOT = $sdkPath

    $localProperties = Join-Path $androidRoot "local.properties"
    $sdkDir = ($sdkPath -replace "\\", "/")
    "sdk.dir=$sdkDir" | Set-Content -Path $localProperties -Encoding ASCII
    Write-Host "Using Android SDK at $sdkPath"
}

if (-not $env:JAVA_HOME) {
    Set-JavaHomeFromAndroidStudio
}

Set-AndroidSdk

Push-Location $webRoot
try {
    npm run cap:icons
    if ($Dev) {
        Write-Host "Building DEV APK (LAN / emulator, no production API in JS)" -ForegroundColor Yellow
        npm run cap:apk:dev
    } else {
        Write-Host "Building PRODUCTION APK (API: https://api.decime.online)" -ForegroundColor Cyan
        npm run cap:apk
    }
} finally {
    Pop-Location
}

$py = Join-Path $repoRoot "apps\api\.venv\Scripts\python.exe"
$e2e = Join-Path $repoRoot "scripts\android_e2e.py"
if ((Test-Path $py) -and (Test-Path $e2e) -and $Dev) {
    $devices = & adb devices 2>&1 | Out-String
    if ($devices -match "device\s*$" -or $devices -match "emulator") {
        Write-Host ""
        Write-Host "Running Android E2E on connected device/emulator..."
        & $py $e2e
        if ($LASTEXITCODE -ne 0) {
            Write-Host "E2E failed - APK is built but not verified. Fix issues and re-run." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "No adb device - skip E2E. For dev E2E: .\scripts\build-android-apk.ps1 -Dev" -ForegroundColor Yellow
    }
}

if (Test-Path $apkPath) {
    Write-Host ""
    Write-Host "APK ready:"
    Write-Host $apkPath
    Write-Host ""
    Write-Host "Copy to your phone and install, or run: adb install -r `"$apkPath`""
} else {
    Write-Host "APK not found. Install Android Studio + SDK, then retry." -ForegroundColor Yellow
    exit 1
}
