#!/usr/bin/env python3
"""Production E2E using in-container JWT (no password in env)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from decime_api.db.user_store import get_user_store
from decime_api.services.auth.jwt_tokens import create_access_token

API_BASE = os.environ.get("DECIME_API_BASE", "https://api.decime.online").rstrip("/")
TEST_AUDIO = Path("/tmp/test-es.mp3")


class E2EResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        print(f"PASS {name}" + (f" — {detail}" if detail else ""))
        self.passed.append(name)

    def fail(self, name: str, detail: str) -> None:
        print(f"FAIL {name} — {detail}", file=sys.stderr)
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
        data = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode(),
                b"Content-Type: audio/mpeg\r\n\r\n",
                file_bytes,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
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


def issue_token() -> str:
    users = get_user_store().list_users()
    if not users:
        raise RuntimeError("No users in store")
    user = next((u for u in users if u.role == "admin"), users[0])
    token, _ = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return token


def main() -> int:
    result = E2EResult()
    print(f"API base: {API_BASE}")

    status, health = request("GET", "/health", timeout=15)
    if status == 200 and isinstance(health, dict) and health.get("status") == "ok":
        result.ok("health", f"llm={health.get('llm_model')}")
    else:
        result.fail("health", f"status={status}")
        return 1

    try:
        token = issue_token()
    except RuntimeError as error:
        result.fail("auth/token", str(error))
        return 1
    result.ok("auth/token", "JWT from user store")

    status, me = request("GET", "/api/v1/auth/me", token=token, timeout=15)
    if status == 200 and isinstance(me, dict):
        result.ok("auth/me", me.get("email", ""))
    else:
        result.fail("auth/me", f"status={status}")

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
        result.ok("translate/text", spanish_reply[:60] if spanish_reply else "empty")
    else:
        result.fail("translate/text", f"status={status} {str(compose)[:120]}")

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
    if status == 200 and isinstance(incoming, dict) and (incoming.get("translation_ru") or "").strip():
        result.ok("incoming/understand-text", (incoming["translation_ru"] or "")[:60])
    else:
        result.fail("incoming/understand-text", f"status={status}")

    status, history = request("GET", "/api/v1/history?limit=5", token=token, timeout=15)
    if status == 200 and isinstance(history, dict):
        result.ok("history/list", f"{len(history.get('items') or [])} items")
    else:
        result.fail("history/list", f"status={status}")

    status, lists = request("GET", "/api/v1/training/lists", token=token, timeout=15)
    list_id = lists[0]["list_id"] if status == 200 and isinstance(lists, list) and lists else None
    if list_id:
        result.ok("training/lists", list_id[:8])
    else:
        result.fail("training/lists", f"status={status}")

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
            ][:2]
            result.ok("training/extract-candidates", f"{len(candidates)} in {elapsed:.1f}s")
        else:
            result.fail("training/extract-candidates", f"status={status} {str(extract)[:120]}")

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
            result.ok("training/approve-candidates", f"created={len(approve.get('created_items') or [])}")
        else:
            result.fail("training/approve-candidates", f"status={status}")

    if list_id:
        status, items = request("GET", f"/api/v1/training/items?list_id={list_id}", token=token, timeout=15)
        if status == 200 and isinstance(items, dict):
            result.ok("training/items", f"{len(items.get('items') or [])} items")
        else:
            result.fail("training/items", f"status={status}")

        status, review = request("GET", f"/api/v1/training/review/next?list_id={list_id}&limit=5", token=token, timeout=15)
        if status == 200 and isinstance(review, dict):
            result.ok("training/review/next", f"{len(review.get('items') or [])} due")
        else:
            result.fail("training/review/next", f"status={status}")

    synth_text = spanish_reply or "Hola, ¿cómo estás?"
    status, synth = request(
        "POST",
        "/api/v1/audio/synthesize",
        token=token,
        body={"text": synth_text, "locale": "es-UY-montevideo", "mode": "reply", "speed": "normal"},
        timeout=120,
    )
    audio_id = synth.get("audio_id") if status == 200 and isinstance(synth, dict) else None
    if audio_id:
        result.ok("audio/synthesize", audio_id[:8])
    else:
        result.fail("audio/synthesize", f"status={status}")

    if audio_id:
        status, file_body = request("GET", f"/api/v1/audio/files/{audio_id}", token=token, timeout=30)
        if status == 200 and isinstance(file_body, bytes) and len(file_body) > 100:
            result.ok("audio/files", f"{len(file_body)} bytes")
        else:
            result.fail("audio/files", f"status={status}")

    if TEST_AUDIO.exists():
        status, transcribe = request(
            "POST",
            "/api/v1/audio/transcribe",
            token=token,
            multipart=("file", TEST_AUDIO.read_bytes(), "test-es.mp3"),
            timeout=120,
        )
        if status == 200 and isinstance(transcribe, dict) and (transcribe.get("transcript") or "").strip():
            result.ok("audio/transcribe", (transcribe["transcript"] or "")[:60])
        else:
            result.fail("audio/transcribe", f"status={status} {str(transcribe)[:120]}")
    else:
        print("SKIP audio/transcribe — no test-es.mp3 in /tmp")

    print()
    print(f"Summary: {len(result.passed)} passed, {len(result.failed)} failed")
    for item in result.failed:
        print(f"  - {item}", file=sys.stderr)
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
