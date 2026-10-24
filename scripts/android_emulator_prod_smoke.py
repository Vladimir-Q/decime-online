#!/usr/bin/env python3
"""Production APK smoke test on Android emulator (https://api.decime.online)."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / "apps" / "web" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
PACKAGE = "com.decime.uy"
PRODUCTION_API = "https://api.decime.online"


def adb_bin() -> str:
    local = Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    return str(local) if local.exists() else "adb"


def adb(*args: str) -> str:
    result = subprocess.run([adb_bin(), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"adb failed: {args}")
    return result.stdout.strip()


def read_conn_state() -> dict:
    log = adb("logcat", "-d", "-s", "Capacitor/Console:I")
    for line in reversed(log.splitlines()):
        marker = "DECIME_CONN_E2E|"
        if marker not in line:
            continue
        payload = line.split(marker, 1)[1].strip()
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            continue
    return {}


def wait_conn(predicate, label: str, seconds: float = 90.0) -> dict:
    deadline = time.time() + seconds
    last: dict = {}
    while time.time() < deadline:
        last = read_conn_state()
        if predicate(last):
            return last
        time.sleep(1.0)
    raise AssertionError(f"{label} — last: {json.dumps(last, ensure_ascii=False)}")


def launch_diagnostics() -> None:
    adb("shell", "am", "force-stop", PACKAGE)
    adb(
        "shell",
        "am",
        "start",
        "-n",
        f"{PACKAGE}/.MainActivity",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        "https://localhost/app/diagnostics/",
    )


def send_e2e(action: str, payload: str | None = None) -> None:
    args = [
        adb_bin(),
        "shell",
        "am",
        "start",
        "-n",
        f"{PACKAGE}/.MainActivity",
        "--activity-single-top",
        "--es",
        "e2e_action",
        action,
    ]
    if payload:
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        args.extend(["--es", "e2e_payload_b64", encoded])
    subprocess.run(args, check=True, capture_output=True, text=True)


def main() -> int:
    print("=== Decime Android PRODUCTION emulator smoke ===\n")

    devices = adb("devices")
    if "emulator" not in devices:
        print("FAIL: no emulator", file=sys.stderr)
        return 1

    try:
        with urllib.request.urlopen(f"{PRODUCTION_API}/health", timeout=15) as response:
            health = json.loads(response.read().decode("utf-8"))
        print(f"OK host can reach {PRODUCTION_API} — {health.get('app')}")
    except Exception as error:
        print(f"WARN host health check skipped ({error}) — testing from app only")

    if not APK.exists():
        print(f"FAIL: APK missing at {APK}", file=sys.stderr)
        return 1

    adb("install", "-r", str(APK))
    adb("logcat", "-c")

    launch_diagnostics()
    time.sleep(6)

    send_e2e("conn-test")
    time.sleep(2)
    state = wait_conn(lambda s: s.get("healthOk") is True, "Production API health from app", seconds=60)
    saved = state.get("savedUrl") or ""
    print(f"OK production health from app — savedUrl={saved} app={state.get('healthApp')}")

    print("\n=== PRODUCTION EMULATOR SMOKE PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"\nFAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
