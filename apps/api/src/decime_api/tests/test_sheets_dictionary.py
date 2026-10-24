"""Dictionary Sheets export/import — fake AI + mocked n8n webhooks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from decime_api.db.sheets_jobs import reset_sheets_job_repository
from decime_api.services.ai.fake_training_extractor import FakeTrainingExtractor
from decime_api.services.training.canonical import build_canonical_key
from decime_api.services.training.display_text import apply_article_to_display
from decime_api.services.training.sheets_service import parse_spreadsheet_id


def _register(client: TestClient, email: str = "sheets@example.com") -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "passwordA1", "display_name": "Sheets"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return token, me.json()["id"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _n8n(key: str = "test-automation-key") -> dict[str, str]:
    return {"X-Decime-Automation-Key": key}


def _configure_sheets(live_settings, monkeypatch) -> None:
    live_settings.n8n_automation_key = "test-automation-key"
    live_settings.n8n_export_webhook_url = "http://n8n.test/webhook/export"
    live_settings.n8n_import_webhook_url = "http://n8n.test/webhook/import"
    live_settings.google_dictionary_spreadsheet_id = "spreadsheet-test-id"
    live_settings.dictionary_sheets_job_timeout_minutes = 30
    monkeypatch.setattr(
        "decime_api.services.training.sheets_service.settings",
        live_settings,
    )


@pytest.fixture
def sheets_settings(auth_client, monkeypatch):
    from decime_api.config import settings as live_settings

    _configure_sheets(live_settings, monkeypatch)
    reset_sheets_job_repository()
    yield live_settings
    reset_sheets_job_repository()


def test_parse_spreadsheet_id_from_url() -> None:
    url = "https://docs.google.com/spreadsheets/d/1FkTZ0ShmhuJTru7BmMn3bSpunuEjiDv3ZmmHca4QIwU/edit"
    assert parse_spreadsheet_id(url).startswith("1FkTZ0")


def test_article_not_doubled() -> None:
    display, surface, grammar = apply_article_to_display(
        display_text="la tarjeta",
        surface_text="la tarjeta",
        grammar={"article": "la", "gender": "feminine"},
    )
    assert display == "la tarjeta"
    assert surface == "la tarjeta"
    assert grammar["article"] == "la"

    display2, _, _ = apply_article_to_display(
        display_text="tarjeta",
        surface_text="tarjeta",
        grammar={"article": "la"},
    )
    assert display2 == "la tarjeta"


def test_idiom_canonical_key() -> None:
    key = build_canonical_key(
        item_type="idiom",
        surface_text="Dar  la  lata",
        lemma=None,
        grammar={},
    )
    assert key == "idiom:dar la lata"


@pytest.mark.asyncio
async def test_fake_normalize_preserves_russian_and_article() -> None:
    extractor = FakeTrainingExtractor()
    noun = await extractor.normalize_dictionary_row(spanish="tarjeta", russian="карточка")
    assert noun.item_type == "noun"
    assert noun.translations_ru == ["карточка"]
    assert noun.display_text.startswith("la ") or noun.display_text.startswith("el ")
    assert noun.display_text.count("la ") <= 1

    idiom = await extractor.normalize_dictionary_row(
        spanish="dar la lata", russian="доставать"
    )
    assert idiom.item_type == "idiom"
    assert idiom.translations_ru == ["доставать"]


def test_export_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/training/sheets/export", json={"list_id": "x"})
    assert response.status_code == 401


def test_export_missing_config(auth_client: TestClient, sheets_settings) -> None:
    sheets_settings.n8n_export_webhook_url = None
    token, _ = _register(auth_client, "cfg@example.com")
    lists = auth_client.get("/api/v1/training/lists", headers=_auth(token))
    list_id = lists.json()[0]["list_id"]
    response = auth_client.post(
        "/api/v1/training/sheets/export",
        headers=_auth(token),
        json={"list_id": list_id},
    )
    assert response.status_code == 503


def test_n8n_routes_closed_without_key(auth_client: TestClient) -> None:
    from decime_api.config import settings as live_settings

    live_settings.n8n_automation_key = None
    response = auth_client.get("/api/v1/integrations/n8n/jobs/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 503


def test_n8n_invalid_key(auth_client: TestClient, sheets_settings) -> None:
    response = auth_client.get(
        "/api/v1/integrations/n8n/jobs/00000000-0000-0000-0000-000000000001",
        headers=_n8n("wrong-key"),
    )
    assert response.status_code == 401


def test_export_import_flow_and_isolation(auth_client: TestClient, sheets_settings) -> None:
    token_a, user_a = _register(auth_client, "exporter-a@example.com")
    token_b, _user_b = _register(auth_client, "owner-b@example.com")

    lists_a = auth_client.get("/api/v1/training/lists", headers=_auth(token_a))
    list_a = lists_a.json()[0]["list_id"]
    lists_b = auth_client.get("/api/v1/training/lists", headers=_auth(token_b))
    list_b = lists_b.json()[0]["list_id"]

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ) as mock_hook:
        export = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token_a),
            json={"list_id": list_a},
        )
        assert export.status_code == 202, export.text
        job_id = export.json()["job_id"]
        assert export.json()["status"] == "running"
        assert mock_hook.await_count == 1
        assert mock_hook.await_args.args[0] == "http://n8n.test/webhook/export"
        payload = mock_hook.await_args.args[1]
        assert payload["job_id"] == job_id
        assert payload["user_id"] == user_a
        assert payload["list_id"] == list_a
        assert payload["sheet_name"] == f"user_{user_a}"
        assert payload["spreadsheet_id"] == "spreadsheet-test-id"

        # Concurrent export blocked
        export2 = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token_a),
            json={"list_id": list_a},
        )
        assert export2.status_code == 409

        # Other user cannot see job
        foreign = auth_client.get(
            f"/api/v1/training/sheets/jobs/{job_id}",
            headers=_auth(token_b),
        )
        assert foreign.status_code == 404

        status = auth_client.get(
            f"/api/v1/training/sheets/jobs/{job_id}",
            headers=_auth(token_a),
        )
        assert status.status_code == 200
        assert status.json()["status"] == "running"

        # n8n context — fields used for SQL + Sheets write
        ctx = auth_client.get(
            f"/api/v1/integrations/n8n/jobs/{job_id}",
            headers=_n8n(),
        )
        assert ctx.status_code == 200
        body = ctx.json()
        assert body["job_id"] == job_id
        assert body["user_id"] == user_a
        assert body["list_id"] == list_a
        assert body["spreadsheet_id"] == "spreadsheet-test-id"
        assert body["sheet_name"] == f"user_{user_a}"
        assert body["status"] == "running"

        complete = auth_client.post(
            f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
            headers=_n8n(),
            json={"status": "completed", "report": {"exported_rows": 0, "message": "empty"}},
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

        # Idempotent complete
        complete2 = auth_client.post(
            f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
            headers=_n8n(),
            json={"status": "failed", "error_message": "late"},
        )
        assert complete2.status_code == 200
        assert complete2.json()["status"] == "completed"

        # Import job
        imp = auth_client.post(
            "/api/v1/training/sheets/import",
            headers=_auth(token_a),
            json={
                "list_id": list_a,
                "source_spreadsheet_id": "https://docs.google.com/spreadsheets/d/abcDEF0123456789xyzABC1234567890/edit",
                "source_sheet_name": "Sheet1",
            },
        )
        assert imp.status_code == 202, imp.text
        import_job = imp.json()["job_id"]

    # Import rows via n8n
    created = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/import-row",
        headers=_n8n(),
        json={"source_row_number": 2, "spanish": "tarjeta", "russian": "карта"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "created"
    item_id = body["item_id"]
    assert item_id

    # Retry same row — no second card
    retry = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/import-row",
        headers=_n8n(),
        json={"source_row_number": 2, "spanish": "tarjeta", "russian": "карта"},
    )
    assert retry.json()["status"] == "created"
    assert retry.json()["item_id"] == item_id

    # Duplicate spanish different row → skipped
    dup = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/import-row",
        headers=_n8n(),
        json={"source_row_number": 3, "spanish": "la tarjeta", "russian": "другое"},
    )
    assert dup.json()["status"] == "skipped_duplicate"

    # Idiom + empty russian
    idiom = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/import-row",
        headers=_n8n(),
        json={"source_row_number": 4, "spanish": "dar la lata", "russian": ""},
    )
    assert idiom.json()["status"] == "created"

    # Empty row
    empty = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/import-row",
        headers=_n8n(),
        json={"source_row_number": 5, "spanish": "  ", "russian": ""},
    )
    assert empty.json()["status"] == "error"

    # Existing card translations unchanged
    items = auth_client.get(
        f"/api/v1/training/items?list_id={list_a}",
        headers=_auth(token_a),
    )
    assert items.status_code == 200
    cards = items.json()["items"]
    tarjeta = next(c for c in cards if "tarjeta" in c["display_text"])
    assert tarjeta["translations_ru"] == ["карта"]

    # User B list still empty / no leak of A's items
    items_b = auth_client.get(
        f"/api/v1/training/items?list_id={list_b}",
        headers=_auth(token_b),
    )
    assert items_b.json()["items"] == []

    done = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/complete",
        headers=_n8n(),
        json={"status": "completed", "report": {}},
    )
    assert done.status_code == 200
    report = done.json()["report"]
    assert report["created"] >= 2
    assert report["skipped"] >= 1
    assert report["errors"] >= 1

    # Import into finished job rejected
    late = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{import_job}/import-row",
        headers=_n8n(),
        json={"source_row_number": 99, "spanish": "pagar", "russian": "платить"},
    )
    assert late.status_code == 409


def test_export_webhook_success_marks_running(
    auth_client: TestClient, sheets_settings
) -> None:
    token, _ = _register(auth_client, "run-ok@example.com")
    lists = auth_client.get("/api/v1/training/lists", headers=_auth(token))
    list_id = lists.json()[0]["list_id"]

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        response = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "running"

    status = auth_client.get(
        f"/api/v1/training/sheets/jobs/{job_id}",
        headers=_auth(token),
    )
    assert status.json()["status"] == "running"
    assert status.json()["finished_at"] is None


def test_export_webhook_exception_before_http_marks_failed(
    auth_client: TestClient, sheets_settings
) -> None:
    """Unicode/header prep errors must not leave the job queued."""
    token, _ = _register(auth_client, "pre-http@example.com")
    lists = auth_client.get("/api/v1/training/lists", headers=_auth(token))
    list_id = lists.json()[0]["list_id"]

    # Non-ASCII automation key fails Latin-1 header encoding before any HTTP call.
    sheets_settings.n8n_automation_key = "секрет-не-ascii"

    captured: dict[str, str] = {}
    from decime_api.services.training import sheets_service as svc

    real_post = svc._post_n8n_webhook

    async def _track(url: str, payload: dict) -> None:
        captured["job_id"] = payload["job_id"]
        await real_post(url, payload)

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new=_track,
    ):
        response = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )

    assert response.status_code == 502
    assert captured["job_id"]
    status = auth_client.get(
        f"/api/v1/training/sheets/jobs/{captured['job_id']}",
        headers=_auth(token),
    )
    body = status.json()
    assert body["status"] == "failed"
    assert body["finished_at"]
    assert "non-ASCII" in (body["error_message"] or "")

    # Lock released — next export allowed
    sheets_settings.n8n_automation_key = "test-automation-key"
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        retry = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert retry.status_code == 202


def test_export_webhook_http_rejection_marks_failed(
    auth_client: TestClient, sheets_settings
) -> None:
    from decime_api.services.training.sheets_service import SheetsN8nError

    token, _ = _register(auth_client, "http-rej@example.com")
    lists = auth_client.get("/api/v1/training/lists", headers=_auth(token))
    list_id = lists.json()[0]["list_id"]

    captured: dict[str, str] = {}

    async def _reject(url: str, payload: dict) -> None:
        captured["job_id"] = payload["job_id"]
        raise SheetsN8nError("n8n webhook rejected the job (500)")

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new=_reject,
    ):
        response = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert response.status_code == 502

    status = auth_client.get(
        f"/api/v1/training/sheets/jobs/{captured['job_id']}",
        headers=_auth(token),
    )
    assert status.json()["status"] == "failed"
    assert status.json()["finished_at"]


def test_complete_completed_and_failed_set_finished_at(
    auth_client: TestClient, sheets_settings
) -> None:
    token, _ = _register(auth_client, "complete-ok@example.com")
    lists = auth_client.get("/api/v1/training/lists", headers=_auth(token))
    list_id = lists.json()[0]["list_id"]

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        export = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    job_id = export.json()["job_id"]

    done = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
        headers=_n8n(),
        json={"status": "completed", "report": {"exported_rows": 3}},
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["finished_at"]

    # Idempotent — stays completed
    again = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
        headers=_n8n(),
        json={"status": "failed", "error_message": "late"},
    )
    assert again.json()["status"] == "completed"

    # Fresh job → failed path
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        export2 = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    job2 = export2.json()["job_id"]
    failed = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job2}/complete",
        headers=_n8n(),
        json={"status": "failed", "error_message": "Create sheet failed", "report": {}},
    )
    assert failed.status_code == 200
    body = failed.json()
    assert body["status"] == "failed"
    assert body["finished_at"]
    assert body["error_message"] == "Create sheet failed"

    # Failed job does not block next export
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        export3 = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert export3.status_code == 202


def _start_export(auth_client: TestClient, token: str, email: str) -> tuple[str, str]:
    listed = auth_client.get("/api/v1/training/lists", headers=_auth(token))
    list_id = listed.json()[0]["list_id"]
    return token, list_id


def test_callback_during_webhook_stays_completed(
    auth_client: TestClient, sheets_settings
) -> None:
    """n8n can finish the job before the webhook HTTP call returns."""
    token, _ = _register(auth_client, "race-done@example.com")
    _, list_id = _start_export(auth_client, token, "race-done@example.com")

    async def _complete_before_return(url: str, payload: dict) -> None:
        from decime_api.db.sheets_jobs import get_sheets_job_repository
        from decime_api.schemas.training import N8nCompleteJobRequest, SheetsJobReport
        from decime_api.services.training.sheets_service import complete_job

        await complete_job(
            payload["job_id"],
            N8nCompleteJobRequest(
                status="completed",
                report=SheetsJobReport(exported_rows=4, message="written"),
            ),
            jobs=get_sheets_job_repository(),
        )

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new=_complete_before_return,
    ):
        response = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "completed"
    status = auth_client.get(
        f"/api/v1/training/sheets/jobs/{body['job_id']}",
        headers=_auth(token),
    )
    assert status.json()["status"] == "completed"
    assert status.json()["finished_at"]
    assert status.json()["report"]["exported_rows"] == 4


def test_timeout_does_not_overwrite_completed_callback(
    auth_client: TestClient, sheets_settings
) -> None:
    token, _ = _register(auth_client, "timeout-done@example.com")
    _, list_id = _start_export(auth_client, token, "timeout-done@example.com")

    async def _complete_then_timeout(url: str, payload: dict) -> None:
        from decime_api.db.sheets_jobs import get_sheets_job_repository
        from decime_api.schemas.training import N8nCompleteJobRequest, SheetsJobReport
        from decime_api.services.training.sheets_service import (
            SheetsN8nError,
            complete_job,
        )

        await complete_job(
            payload["job_id"],
            N8nCompleteJobRequest(
                status="completed",
                report=SheetsJobReport(exported_rows=2),
            ),
            jobs=get_sheets_job_repository(),
        )
        raise SheetsN8nError("n8n webhook timed out")

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new=_complete_then_timeout,
    ):
        response = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "completed"
    status = auth_client.get(
        f"/api/v1/training/sheets/jobs/{body['job_id']}",
        headers=_auth(token),
    )
    assert status.json()["status"] == "completed"
    assert status.json()["error_message"] is None


def test_callback_after_timeout_does_not_resurrect_job(
    auth_client: TestClient, sheets_settings
) -> None:
    token, _ = _register(auth_client, "late-cb@example.com")
    _, list_id = _start_export(auth_client, token, "late-cb@example.com")
    captured: dict[str, str] = {}

    async def _timeout(url: str, payload: dict) -> None:
        from decime_api.services.training.sheets_service import SheetsN8nError

        captured["job_id"] = payload["job_id"]
        raise SheetsN8nError("n8n webhook timed out")

    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new=_timeout,
    ):
        response = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert response.status_code == 502
    job_id = captured["job_id"]
    late = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
        headers=_n8n(),
        json={
            "status": "completed",
            "report": {"exported_rows": 9},
            "error_message": None,
        },
    )
    assert late.status_code == 200
    body = late.json()
    assert body["status"] == "failed"
    assert body["finished_at"]
    assert "timed out" in (body["error_message"] or "")
    assert body["report"].get("exported_rows") is None


def test_repeat_failed_callback_keeps_first_error(
    auth_client: TestClient, sheets_settings
) -> None:
    token, _ = _register(auth_client, "fail-twice@example.com")
    _, list_id = _start_export(auth_client, token, "fail-twice@example.com")
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        export = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    job_id = export.json()["job_id"]
    first = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
        headers=_n8n(),
        json={"status": "failed", "error_message": "sheet locked", "report": {}},
    )
    assert first.json()["status"] == "failed"
    second = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
        headers=_n8n(),
        json={"status": "failed", "error_message": "different", "report": {"exported_rows": 1}},
    )
    assert second.json()["status"] == "failed"
    assert second.json()["error_message"] == "sheet locked"
    assert second.json()["finished_at"] == first.json()["finished_at"]


def test_empty_export_completion(auth_client: TestClient, sheets_settings) -> None:
    token, _ = _register(auth_client, "empty-export@example.com")
    _, list_id = _start_export(auth_client, token, "empty-export@example.com")
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        export = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    done = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{export.json()['job_id']}/complete",
        headers=_n8n(),
        json={"status": "completed", "report": {"exported_rows": 0, "message": "No rows"}},
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["finished_at"]
    assert done.json()["report"]["exported_rows"] == 0


def test_second_export_while_running_is_conflict(
    auth_client: TestClient, sheets_settings
) -> None:
    token, _ = _register(auth_client, "two-export@example.com")
    _, list_id = _start_export(auth_client, token, "two-export@example.com")
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        first = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
        second = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    assert first.status_code == 202
    assert second.status_code == 409


def test_stale_job_fails_on_poll_and_ignores_later_success(
    auth_client: TestClient, sheets_settings
) -> None:
    """After a restart the job row is the only state; polling records the timeout."""
    from datetime import UTC, datetime, timedelta

    from decime_api.db.sheets_jobs import MemorySheetsJobRepository, get_sheets_job_repository

    token, _ = _register(auth_client, "stale-job@example.com")
    _, list_id = _start_export(auth_client, token, "stale-job@example.com")
    with patch(
        "decime_api.services.training.sheets_service._post_n8n_webhook",
        new_callable=AsyncMock,
    ):
        export = auth_client.post(
            "/api/v1/training/sheets/export",
            headers=_auth(token),
            json={"list_id": list_id},
        )
    job_id = export.json()["job_id"]
    repo = get_sheets_job_repository()
    assert isinstance(repo, MemorySheetsJobRepository)
    repo._jobs[job_id].updated_at = datetime.now(UTC) - timedelta(minutes=10)
    sheets_settings.dictionary_sheets_job_timeout_minutes = 1

    status = auth_client.get(
        f"/api/v1/training/sheets/jobs/{job_id}",
        headers=_auth(token),
    )
    assert status.json()["status"] == "failed"
    assert status.json()["finished_at"]
    assert "timed out" in (status.json()["error_message"] or "")

    late = auth_client.post(
        f"/api/v1/integrations/n8n/jobs/{job_id}/complete",
        headers=_n8n(),
        json={"status": "completed", "report": {"exported_rows": 3}},
    )
    assert late.json()["status"] == "failed"
    assert late.json()["report"].get("exported_rows") is None
