#!/usr/bin/env python3
"""Emulator E2E for Decime Android Quick Reply (android_setup.md flows)."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / "apps" / "web" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
TEST_AUDIO = ROOT / "test-es.mp3"
PACKAGE = "com.decime.uy"
API_EMULATOR = "http://10.0.2.2:8000"
API_HOST = "http://127.0.0.1:8000"
# Required so NativeShareBootstrap does not clear pending share prefs on cold start.
FORCE_QR_PREF = "    <string name=\"decime_force_quick_reply\">1</string>"


def adb_bin() -> str:
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk:
        candidate = Path(sdk) / "platform-tools" / "adb.exe"
        if candidate.exists():
            return str(candidate)
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    if local.exists():
        return str(local)
    return "adb"


def adb(*args: str) -> str:
    result = subprocess.run(
        [adb_bin(), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"adb failed: {args}")
    return result.stdout.strip()


def http_get(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_api() -> None:
    for _ in range(20):
        try:
            data = http_get(f"{API_HOST}/health", timeout=2.0)
            if data.get("status") == "ok":
                print(f"OK API health: {data.get('app')}")
                return
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.5)
    raise RuntimeError(f"API not reachable at {API_HOST}/health — start uvicorn --host 0.0.0.0 --port 8000")


def ensure_test_audio() -> None:
    if TEST_AUDIO.exists():
        return
    print("Generating test-es.mp3 via gTTS...")
    py = ROOT / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
    subprocess.run(
        [
            str(py),
            "-c",
            "from gtts import gTTS; gTTS('Hola, como estas? Todo bien.', lang='es').save(r'"
            + str(TEST_AUDIO).replace("\\", "\\\\")
            + "')",
        ],
        check=True,
    )


def write_prefs(xml: str) -> None:
    tmp = ROOT / ".tmp_cap_prefs.xml"
    tmp.write_text(xml, encoding="utf-8")
    adb("push", str(tmp), "/data/local/tmp/CapacitorStorage.xml")
    adb("shell", "run-as", PACKAGE, "cp", "/data/local/tmp/CapacitorStorage.xml", "shared_prefs/CapacitorStorage.xml")


def launch_app(clear_log: bool = True) -> None:
    if clear_log:
        adb("logcat", "-c")
    adb("shell", "am", "force-stop", PACKAGE)
    adb("shell", "am", "start", "-n", f"{PACKAGE}/.MainActivity")


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


def wait_e2e(predicate, label: str, seconds: float = 90.0) -> dict:
    deadline = time.time() + seconds
    last: dict = {}
    while time.time() < deadline:
        last = read_e2e_state()
        if predicate(last):
            return last
        time.sleep(1.0)
    raise AssertionError(f"{label} — last state: {json.dumps(last, ensure_ascii=False)}")


def launch_diagnostics(clear_log: bool = False) -> None:
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
        "https://localhost/app/diagnostics/",
    )


def send_e2e_action_on_page(action: str, payload: str | None = None) -> None:
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
    if payload is not None:
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        args.extend(["--es", "e2e_payload_b64", encoded])
    subprocess.run(args, check=True, capture_output=True, text=True)


def read_conn_e2e_state() -> dict:
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


def wait_conn_e2e(predicate, label: str, seconds: float = 60.0) -> dict:
    deadline = time.time() + seconds
    last: dict = {}
    while time.time() < deadline:
        last = read_conn_e2e_state()
        if predicate(last):
            return last
        time.sleep(1.0)
    raise AssertionError(f"{label} — last state: {json.dumps(last, ensure_ascii=False)}")


def send_e2e_action(action: str) -> None:
    send_e2e_action_on_page(action)


def send_generate(intent: str) -> None:
    send_e2e_action_on_page("generate", intent)


def main() -> int:
    print("=== Decime Android E2E ===\n")

    devices = adb("devices")
    if "device" not in devices.replace("List of devices attached", ""):
        print("FAIL: no adb device/emulator", file=sys.stderr)
        return 1

    wait_api()
    ensure_test_audio()

    if not APK.exists():
        print(f"FAIL: APK missing at {APK}", file=sys.stderr)
        return 1

    print(f"Installing {APK.name}...")
    adb("install", "-r", str(APK))
    adb("push", str(TEST_AUDIO), "/data/local/tmp/test-es.mp3")
    adb("shell", "run-as", PACKAGE, "cp", "/data/local/tmp/test-es.mp3", "cache/decime-test-audio.mp3")

    # 1) Share text prefilled
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{API_EMULATOR}</string>
{FORCE_QR_PREF}
    <string name="decime_pending_share_text">Podés pasar mañana después de las 10?</string>
</map>"""
    )
    launch_app()
    time.sleep(5)
    state = wait_e2e(
        lambda s: "mañana" in (s.get("incomingText") or "")
        or "manana" in (s.get("incomingText") or "").lower()
        or "10" in (s.get("incomingText") or ""),
        "Share text prefilled",
    )
    print(f"OK share text: {(state.get('incomingText') or '')[:70]}")

    # 2) Translate (same session — intent extra)
    send_e2e_action("translate")
    time.sleep(2)
    state = wait_e2e(
        lambda s: bool((s.get("translation") or "").strip())
        and not s.get("understandLoading")
        and not (s.get("error") or "").strip(),
        "Translate shows translation",
        seconds=120,
    )
    print(f"OK translate: {(state.get('translation') or '')[:80]}")

    # 3) Generate Spanish reply
    send_generate("Si, manana despues de las 10 me viene bien, gracias")
    time.sleep(2)
    state = wait_e2e(
        lambda s: len((s.get("replySpanish") or "").strip()) >= 8
        and not s.get("replyLoading")
        and not (s.get("error") or "").strip(),
        "Generate Spanish reply",
        seconds=180,
    )
    print(f"OK reply: {(state.get('replySpanish') or '')[:80]}")

    # 4) Share audio → transcript
    audio_url = "https://localhost/_capacitor_file_/data/user/0/com.decime.uy/cache/decime-test-audio.mp3"
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{API_EMULATOR}</string>
{FORCE_QR_PREF}
    <string name="decime_pending_share_audio_uri">{audio_url}</string>
</map>"""
    )
    launch_app()
    time.sleep(5)
    state = wait_e2e(
        lambda s: bool((s.get("incomingText") or "").strip())
        and not s.get("audioLoading")
        and "empty" not in (s.get("error") or "").lower(),
        "Audio share transcribed to incoming field",
        seconds=90,
    )
    print(f"OK audio transcript: {(state.get('incomingText') or '')[:80]}")

    # 5) Paste text (clipboard + Capacitor Clipboard plugin)
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{API_EMULATOR}</string>
{FORCE_QR_PREF}
    <string name="decime_e2e_paste_text">Hola probando paste</string>
</map>"""
    )
    launch_app(clear_log=False)
    time.sleep(5)
    adb("shell", "cmd", "clipboard", "set-text", "Hola probando paste")
    time.sleep(1)
    send_e2e_action("paste")
    time.sleep(3)
    state = wait_e2e(
        lambda s: "probando" in (s.get("incomingText") or "").lower(),
        "Paste text from clipboard",
        seconds=30,
    )
    print(f"OK paste text: {(state.get('incomingText') or '')[:70]}")

    # 6) Stale example IP replaced with emulator API URL
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{API_EMULATOR}</string>
</map>"""
    )
    launch_diagnostics(clear_log=True)
    time.sleep(6)
    send_e2e_action_on_page("conn-test")
    conn = wait_conn_e2e(
        lambda s: s.get("healthOk") is True and s.get("savedUrl") == API_EMULATOR,
        "Health OK on emulator API URL",
        seconds=60,
    )
    print(f"OK emulator API URL: {conn.get('savedUrl')}")

    # 7) Translate with correct URL
    write_prefs(
        f"""<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="decime_api_base_url">{API_EMULATOR}</string>
{FORCE_QR_PREF}
    <string name="decime_pending_share_text">Hola conexion</string>
</map>"""
    )
    launch_app(clear_log=True)
    time.sleep(5)
    send_e2e_action("translate")
    time.sleep(2)
    state = wait_e2e(
        lambda s: bool((s.get("translation") or "").strip())
        and not s.get("understandLoading")
        and not (s.get("error") or "").strip(),
        "Correct emulator API URL connects",
        seconds=120,
    )
    print(f"OK good URL translate: {(state.get('translation') or '')[:80]}")

    print("\n=== ALL E2E TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"\nFAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f"\nFAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
