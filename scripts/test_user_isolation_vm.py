#!/usr/bin/env python3
"""VM E2E: two users must not see each other's training / history / audio."""

from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.error
import urllib.request

from decime_api.db.user_store import get_user_store
from decime_api.services.auth.jwt_tokens import create_access_token

API_BASE = os.environ.get("DECIME_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict | list | str | bytes]:
    url = f"{API_BASE}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
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


def token_for(email: str) -> str:
    user = get_user_store().get_by_email(email)
    if user is None:
        raise RuntimeError(f"user not found: {email}")
    token, _ = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return token


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    email_a = f"iso-a-{suffix}@example.com"
    email_b = f"iso-b-{suffix}@example.com"
    password = f"IsoTest-{suffix}!"

    store = get_user_store()
    users = store.list_users()
    admin = next((u for u in users if u.role == "admin"), None)
    if admin is None:
        print("FAIL no admin user", file=sys.stderr)
        return 1
    admin_token, _ = create_access_token(user_id=admin.id, email=admin.email, role=admin.role)

    for email in (email_a, email_b):
        status, created = request(
            "POST",
            "/api/v1/auth/users",
            token=admin_token,
            body={"email": email, "password": password, "role": "user", "is_active": True},
        )
        if status != 201:
            print(f"FAIL create {email}: {status} {created}", file=sys.stderr)
            return 1

    token_a = token_for(email_a)
    token_b = token_for(email_b)
    failed = 0

    status, compose = request(
        "POST",
        "/api/v1/translate/text",
        token=token_a,
        body={"source_text": "Нужна карта для оплаты."},
    )
    if status != 200:
        print(f"FAIL compose A: {status}", file=sys.stderr)
        failed += 1

    status, lists_a = request("GET", "/api/v1/training/lists", token=token_a)
    list_a = lists_a[0]["list_id"] if status == 200 and isinstance(lists_a, list) and lists_a else None
    if not list_a:
        print(f"FAIL lists A: {status}", file=sys.stderr)
        return 1

    status, extract = request(
        "POST",
        "/api/v1/training/extract-candidates",
        token=token_a,
        body={
            "source_type": "generated_reply",
            "source_language": "ru",
            "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
            "list_id": list_a,
        },
        timeout=120,
    )
    if status != 200 or not isinstance(extract, dict):
        print(f"FAIL extract A: {status} {extract}", file=sys.stderr)
        return 1
    candidate_ids = [
        c["candidate_id"]
        for c in (extract.get("candidates") or [])
        if c.get("status_hint") != "duplicate_possible"
    ][:1]
    status, approve = request(
        "POST",
        "/api/v1/training/approve-candidates",
        token=token_a,
        body={
            "list_id": list_a,
            "extraction_id": extract["extraction_id"],
            "approved_candidate_ids": candidate_ids,
            "generate_audio": False,
        },
    )
    if status != 200:
        print(f"FAIL approve A: {status} {approve}", file=sys.stderr)
        failed += 1

    status, synth = request(
        "POST",
        "/api/v1/audio/synthesize",
        token=token_a,
        body={"text": "Hola aislamiento", "locale": "es-UY-montevideo"},
        timeout=120,
    )
    audio_id = synth.get("audio_id") if status == 200 and isinstance(synth, dict) else None
    if not audio_id:
        print(f"FAIL synth A: {status}", file=sys.stderr)
        failed += 1

    # Cross-user checks
    status, hist_b = request("GET", "/api/v1/history?limit=20", token=token_b)
    if status == 200 and isinstance(hist_b, dict) and hist_b.get("total", 1) == 0:
        print("PASS history isolation")
    else:
        print(f"FAIL history isolation: {status} {hist_b}", file=sys.stderr)
        failed += 1

    status, items_b = request("GET", f"/api/v1/training/items?list_id={list_a}", token=token_b)
    if status == 404 or (status == 200 and isinstance(items_b, dict) and not items_b.get("items")):
        print("PASS training list isolation")
    else:
        print(f"FAIL training list isolation: {status} {items_b}", file=sys.stderr)
        failed += 1

    if audio_id:
        status, audio_b = request("GET", f"/api/v1/audio/files/{audio_id}", token=token_b)
        if status == 404:
            print("PASS audio isolation")
        else:
            print(f"FAIL audio isolation: {status}", file=sys.stderr)
            failed += 1

        status, audio_a = request("GET", f"/api/v1/audio/files/{audio_id}", token=token_a)
        if status == 200:
            print("PASS audio owner access")
        else:
            print(f"FAIL audio owner access: {status}", file=sys.stderr)
            failed += 1

    status, items_a = request("GET", f"/api/v1/training/items?list_id={list_a}", token=token_a)
    if status == 200 and isinstance(items_a, dict) and len(items_a.get("items") or []) >= 1:
        print("PASS training owner access")
    else:
        print(f"FAIL training owner access: {status} {items_a}", file=sys.stderr)
        failed += 1

    # Cleanup: deactivate test users
    for email in (email_a, email_b):
        user = store.get_by_email(email)
        if user:
            store.update_user(user.id, is_active=False)

    print(f"Summary: failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
