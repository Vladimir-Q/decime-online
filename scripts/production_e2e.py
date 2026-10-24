#!/usr/bin/env python3
"""End-to-end smoke test against production Decime API (HTTPS)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("DECIME_API_BASE", "https://api.decime.online").rstrip("/")
EMAIL = os.environ.get("DECIME_E2E_EMAIL", "admin@decime.online")
PASSWORD = os.environ.get("DECIME_E2E_PASSWORD", "")

ROOT = Path(__file__).resolve().parents[1]
TEST_AUDIO = ROOT / "test-es.mp3"


class E2EResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        msg = f"PASS {name}" + (f" — {detail}" if detail else "")
        print(msg)
        self.passed.append(name)

    def fail(self, name: str, detail: str) -> None:
        msg = f"FAIL {name} — {detail}"
        print(msg, file=sys.stderr)
        self.failed.append(f"{name}: {detail}")


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict | None = None,
    multipart: tuple[str, bytes, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict | str | bytes]:
    url = f"{API_BASE}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data: bytes | None = None
    if multipart:
        boundary = "----DecimeE2EBoundary"
        field_name, file_bytes, filename = multipart
        parts = [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: audio/mpeg\r\n\r\n",
            file_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            ctype = response.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return response.status, json.loads(raw.decode("utf-8"))
            return response.status, raw
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return error.code, parsed


def main() -> int:
    result = E2EResult()
    if not PASSWORD:
        print("Set DECIME_E2E_PASSWORD (or pass via env on VM).", file=sys.stderr)
        return 2

    # Health (no auth)
    status, health = request("GET", "/health", timeout=15)
    if status == 200 and isinstance(health, dict) and health.get("status") == "ok":
        result.ok("health", f"llm={health.get('llm_model')}")
    else:
        result.fail("health", f"status={status} body={health!r}")
        return 1

    # Auth config
    status, auth_cfg = request("GET", "/api/v1/auth/config", timeout=15)
    if status == 200 and isinstance(auth_cfg, dict):
        result.ok("auth/config", f"enabled={auth_cfg.get('auth_enabled')}")
    else:
        result.fail("auth/config", f"status={status}")

    # Login
    status, login = request(
        "POST",
        "/api/v1/auth/login",
        body={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    if status != 200 or not isinstance(login, dict) or not login.get("access_token"):
        result.fail("auth/login", f"status={status} body={login!r}")
        return 1
    token = login["access_token"]
    result.ok("auth/login", EMAIL)

    # Me
    status, me = request("GET", "/api/v1/auth/me", token=token, timeout=15)
    if status == 200 and isinstance(me, dict) and me.get("email"):
        result.ok("auth/me", me["email"])
    else:
        result.fail("auth/me", f"status={status}")

    # Compose (Quick Reply / Live RU→ES)
    status, compose = request(
        "POST",
        "/api/v1/translate/text",
        token=token,
        body={
            "source_language": "ru",
            "source_text": "Привет, как дела?",
            "context": {
                "target_locale": "es-UY-montevideo",
                "channel": "in_person",
                "tone": "polite_neutral",
                "user_level": "A2",
                "situation": None,
            },
        },
        timeout=60,
    )
    spanish_reply = ""
    if status == 200 and isinstance(compose, dict):
        spanish_reply = (compose.get("recommended_reply") or "").strip()
        if spanish_reply:
            result.ok("translate/text", spanish_reply[:60])
        else:
            result.fail("translate/text", "empty recommended_reply")
    else:
        result.fail("translate/text", f"status={status} body={str(compose)[:200]}")

    # Incoming understand (Live ES→RU)
    status, incoming = request(
        "POST",
        "/api/v1/incoming/understand-text",
        token=token,
        body={
            "source_text": "Todo bien, ¿y vos?",
            "source_language": "es",
            "target_language": "ru",
            "locale_variant": "es-UY-montevideo",
            "channel": "in_person",
        },
        timeout=60,
    )
    if status == 200 and isinstance(incoming, dict):
        ru = (incoming.get("translation_ru") or "").strip()
        if ru:
            result.ok("incoming/understand-text", ru[:60])
        else:
            result.fail("incoming/understand-text", "empty translation_ru")
    else:
        result.fail("incoming/understand-text", f"status={status}")

    # History
    status, history = request("GET", "/api/v1/history?limit=5", token=token, timeout=15)
    if status == 200 and isinstance(history, dict):
        count = len(history.get("items") or [])
        result.ok("history/list", f"{count} item(s)")
    else:
        result.fail("history/list", f"status={status}")

    # Training lists
    status, lists = request("GET", "/api/v1/training/lists", token=token, timeout=15)
    list_id = None
    if status == 200 and isinstance(lists, list) and lists:
        list_id = lists[0].get("list_id")
        result.ok("training/lists", f"list_id={list_id[:8] if list_id else '?'}")
    else:
        result.fail("training/lists", f"status={status} body={lists!r}")

    extraction_id = None
    candidate_ids: list[str] = []
    if list_id and spanish_reply:
        t0 = time.monotonic()
        status, extract = request(
            "POST",
            "/api/v1/training/extract-candidates",
            token=token,
            body={
                "source_type": "generated_reply",
                "source_language": "ru",
                "source_original_text": "Привет, как дела?",
                "spanish_text": spanish_reply,
                "list_id": list_id,
            },
            timeout=120,
        )
        elapsed = time.monotonic() - t0
        if status == 200 and isinstance(extract, dict):
            extraction_id = extract.get("extraction_id")
            candidates = extract.get("candidates") or []
            candidate_ids = [
                c["candidate_id"]
                for c in candidates
                if c.get("candidate_id") and c.get("status_hint") != "duplicate_possible"
            ][:3]
            result.ok(
                "training/extract-candidates",
                f"{len(candidates)} candidates in {elapsed:.1f}s",
            )
        else:
            result.fail("training/extract-candidates", f"status={status} body={str(extract)[:200]}")

    if list_id and extraction_id and candidate_ids:
        status, approve = request(
            "POST",
            "/api/v1/training/approve-candidates",
            token=token,
            body={
                "list_id": list_id,
                "extraction_id": extraction_id,
                "approved_candidate_ids": candidate_ids,
                "generate_audio": False,
            },
            timeout=60,
        )
        if status == 200 and isinstance(approve, dict):
            created = len(approve.get("created_items") or [])
            result.ok("training/approve-candidates", f"created={created}")
        else:
            result.fail("training/approve-candidates", f"status={status} body={str(approve)[:200]}")

    if list_id:
        status, items = request(
            "GET",
            f"/api/v1/training/items?list_id={list_id}",
            token=token,
            timeout=15,
        )
        if status == 200 and isinstance(items, dict):
            count = len(items.get("items") or [])
            result.ok("training/items", f"{count} item(s)")
        else:
            result.fail("training/items", f"status={status}")

        status, review = request(
            "GET",
            f"/api/v1/training/review/next?list_id={list_id}&limit=5",
            token=token,
            timeout=15,
        )
        if status == 200 and isinstance(review, dict):
            count = len(review.get("items") or [])
            result.ok("training/review/next", f"{count} due")
        else:
            result.fail("training/review/next", f"status={status}")

    # Audio synthesize
    synth_text = spanish_reply or "Hola, ¿cómo estás?"
    status, synth = request(
        "POST",
        "/api/v1/audio/synthesize",
        token=token,
        body={
            "text": synth_text,
            "locale": "es-UY-montevideo",
            "mode": "reply",
            "speed": "normal",
        },
        timeout=120,
    )
    audio_id = None
    if status == 200 and isinstance(synth, dict):
        audio_id = synth.get("audio_id")
        result.ok("audio/synthesize", f"audio_id={audio_id[:8] if audio_id else '?'}")
    else:
        result.fail("audio/synthesize", f"status={status} body={str(synth)[:200]}")

    # Audio file fetch (Play audio)
    if audio_id:
        status, file_body = request(
            "GET",
            f"/api/v1/audio/files/{audio_id}",
            token=token,
            timeout=30,
        )
        if status == 200 and isinstance(file_body, bytes) and len(file_body) > 100:
            result.ok("audio/files", f"{len(file_body)} bytes")
        else:
            result.fail("audio/files", f"status={status} size={len(file_body) if isinstance(file_body, bytes) else 0}")

    # Transcribe (STT)
    if TEST_AUDIO.exists():
        audio_bytes = TEST_AUDIO.read_bytes()
        status, transcribe = request(
            "POST",
            "/api/v1/audio/transcribe",
            token=token,
            multipart=("file", audio_bytes, "test-es.mp3"),
            timeout=120,
        )
        if status == 200 and isinstance(transcribe, dict):
            transcript = (transcribe.get("transcript") or "").strip()
            if transcript:
                result.ok("audio/transcribe", transcript[:60])
            else:
                result.fail("audio/transcribe", "empty transcript")
        else:
            result.fail("audio/transcribe", f"status={status} body={str(transcribe)[:200]}")
    else:
        print("SKIP audio/transcribe — test-es.mp3 not found locally")

    print()
    print(f"Summary: {len(result.passed)} passed, {len(result.failed)} failed")
    if result.failed:
        for item in result.failed:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
