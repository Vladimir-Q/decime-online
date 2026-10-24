#!/usr/bin/env python3
"""Emulator tests: in-app navigation (Live Chat, Training, Settings)."""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / "apps" / "web" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
PACKAGE = "com.decime.uy"
API_EMULATOR = "http://10.0.2.2:8000"


def adb_bin() -> str:
    local = Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    return str(local) if local.exists() else "adb"


def adb(*args: str) -> str:
    result = subprocess.run([adb_bin(), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"adb failed: {args}")
    return result.stdout.strip()


def write_prefs(xml: str) -> None:
    tmp = ROOT / ".tmp_nav_prefs.xml"
    tmp.write_text(xml, encoding="utf-8")
    adb("push", str(tmp), "/data/local/tmp/CapacitorStorage.xml")
    adb("shell", "run-as", PACKAGE, "cp", "/data/local/tmp/CapacitorStorage.xml", "shared_prefs/CapacitorStorage.xml")


def launch(path: str) -> None:
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
        f"https://localhost{path}",
    )


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


def wait_text(needles: list[str], label: str, seconds: float = 20.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        blob = ui_text_blob()
        if all(needle in blob for needle in needles):
            print(f"OK {label}")
            return
        time.sleep(1.0)
    raise AssertionError(f"{label} — UI missing {needles}. Sample: {ui_text_blob()[:500]!r}")


def tap_link_text(text: str) -> None:
    adb("shell", "uiautomator", "dump", "/sdcard/decime_ui.xml")
    local = ROOT / ".tmp_decime_ui.xml"
    adb("pull", "/sdcard/decime_ui.xml", str(local))
    tree = ET.parse(local)
    target = text.lower()

    def tap_bounds(bounds: str) -> None:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if not m:
            return
        x1, y1, x2, y2 = map(int, m.groups())
        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))

    for node in tree.iter("node"):
        node_text = node.attrib.get("text", "").lower()
        if target not in node_text:
            continue
        if node.attrib.get("clickable") == "true":
            bounds = node.attrib.get("bounds", "")
            if bounds:
                tap_bounds(bounds)
                return
        bounds = node.attrib.get("bounds", "")
        if bounds:
            tap_bounds(bounds)
            return

    raise AssertionError(f"Could not tap link {text!r}")


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


def read_nav_state() -> dict:
    log = adb("logcat", "-d", "-s", "Capacitor/Console:I")
    for line in reversed(log.splitlines()):
        marker = "DECIME_NAV_E2E|"
        if marker not in line:
            continue
        payload = line.split(marker, 1)[1].strip()
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            continue
    return {}


def navigate_in_app(path: str) -> None:
    adb("logcat", "-c")
    send_e2e("nav", path)
    time.sleep(2)


def test_nav(path: str, needles: list[str], label: str) -> None:
    navigate_in_app(path)
    time.sleep(3)
    wait_text(needles, label)
    state = read_nav_state()
    if state.get("pathname") and "index.html" not in state.get("pathname", ""):
        print(f"WARN pathname without index.html: {state.get('pathname')}")


def main() -> int:
    print("=== Android navigation E2E ===\n")

    if "emulator" not in adb("devices"):
        print("FAIL: no emulator", file=sys.stderr)
        return 1
    if not APK.exists():
        print(f"FAIL: missing APK {APK}", file=sys.stderr)
        return 1

    adb("install", "-r", str(APK))
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{API_EMULATOR}</string>
</map>"""
    )

    launch("/app/quick-reply/index.html")
    time.sleep(5)
    wait_text(["quick reply", "live chat"], "Quick Reply nav visible")

    test_nav("/app/live/", ["in-person translation"], "Live Chat via in-app nav")
    test_nav("/app/training/", ["training"], "Training via in-app nav")
    test_nav("/app/settings/", ["api connection"], "Settings via in-app nav")
    test_nav("/app/history/", ["history"], "History via in-app nav")

    print("\n=== NAVIGATION TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"\nFAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
