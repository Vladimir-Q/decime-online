#!/usr/bin/env python3
"""Emulator tests for session expiry -> login redirect (production API)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / "apps" / "web" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
PACKAGE = "com.decime.uy"
PRODUCTION_API = "https://api.decime.online"
# Intentionally malformed; must not look like a real credential to secret scanners.
INVALID_TOKEN = "invalid-session-token-for-e2e"


def adb_bin() -> str:
    local = Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    return str(local) if local.exists() else "adb"


def adb(*args: str) -> str:
    result = subprocess.run([adb_bin(), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"adb failed: {args}")
    return result.stdout.strip()


def write_prefs(xml: str) -> None:
    tmp = ROOT / ".tmp_session_prefs.xml"
    tmp.write_text(xml, encoding="utf-8")
    adb("push", str(tmp), "/data/local/tmp/CapacitorStorage.xml")
    adb("shell", "run-as", PACKAGE, "cp", "/data/local/tmp/CapacitorStorage.xml", "shared_prefs/CapacitorStorage.xml")


def launch_quick_reply(clear_log: bool = True) -> None:
    if clear_log:
        adb("logcat", "-c")
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
        "https://localhost/app/quick-reply/index.html",
    )


def send_translate() -> None:
    adb(
        "shell",
        "am",
        "start",
        "-n",
        f"{PACKAGE}/.MainActivity",
        "--activity-single-top",
        "--es",
        "e2e_action",
        "translate",
    )


def read_e2e_state() -> dict:
    log = adb("logcat", "-d", "-s", "Capacitor/Console:I")
    for line in reversed(log.splitlines()):
        marker = "DECIME_E2E_STATE|"
        if marker not in line:
            continue
        payload = line.split(marker, 1)[1].strip()
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            continue
    return {}


def ui_text_blob() -> str:
    adb("shell", "uiautomator", "dump", "/sdcard/decime_ui.xml")
    local = ROOT / ".tmp_decime_ui.xml"
    adb("pull", "/sdcard/decime_ui.xml", str(local))
    if not local.exists():
        return ""
    try:
        tree = ET.parse(local)
        return " ".join(node.attrib.get("text", "") for node in tree.iter("node")).lower()
    except ET.ParseError:
        return local.read_text(encoding="utf-8", errors="replace").lower()


def on_login_screen() -> bool:
    blob = ui_text_blob()
    return "sign in" in blob or "log in" in blob or "email" in blob and "password" in blob


def wait_login(label: str, seconds: float = 25.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if on_login_screen():
            print(f"OK {label}")
            return
        time.sleep(1.0)
    blob = ui_text_blob()[:400]
    raise AssertionError(f"{label} — UI did not show login. Sample: {blob!r}")


def main() -> int:
    print("=== Session redirect E2E (emulator) ===\n")

    if "emulator" not in adb("devices"):
        print("FAIL: no emulator", file=sys.stderr)
        return 1

    if not APK.exists():
        print(f"FAIL: APK missing at {APK}", file=sys.stderr)
        return 1

    adb("install", "-r", str(APK))

    # 1) Invalid JWT on cold start -> login screen
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{PRODUCTION_API}</string>
    <string name="decime_auth_token">{INVALID_TOKEN}</string>
    <string name="decime_pending_share_text">Hola sesion</string>
</map>"""
    )
    launch_quick_reply()
    time.sleep(8)
    wait_login("invalid token on startup redirects to login")

    # 2) After redirect, translate must not run on Quick Reply (still on login)
    state = read_e2e_state()
    if state.get("translation"):
        raise AssertionError("translate ran despite invalid session")
    print("OK translate blocked before login")

    # 3) No token -> login on protected route
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{PRODUCTION_API}</string>
</map>"""
    )
    launch_quick_reply()
    time.sleep(6)
    wait_login("missing token redirects to login")

    # 4) Invalid token + translate action -> login (mid-session expiry simulation)
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{PRODUCTION_API}</string>
    <string name="decime_auth_token">{INVALID_TOKEN}</string>
    <string name="decime_pending_share_text">Podés pasar mañana?</string>
</map>"""
    )
    launch_quick_reply(clear_log=True)
    time.sleep(5)
    send_translate()
    time.sleep(6)
    wait_login("401 during translate redirects to login")
    state = read_e2e_state()
    if state.get("translation") and not state.get("error"):
        raise AssertionError("got translation without valid session")
    print("OK no successful translate after 401")

    print("\n=== SESSION REDIRECT TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"\nFAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
