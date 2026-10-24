# n8n workflows

Decime runtime **does** call n8n for dictionary Google Sheets export/import (webhooks).  
Analytics / reporting workflows may still poll Postgres `event_log` separately.

Do **not** store secrets in git. Configure `N8N_AUTOMATION_KEY` in Decime `deploy/.env` and the same value in n8n Header Auth credentials.

## Dictionary Sheets integration (app contract)

End-to-end readiness requires a manually built n8n workflow. The app ships API + jobs; Google Sheets and n8n nodes are configured by the operator.

### Environment (Decime API)

| Variable | Purpose |
|----------|---------|
| `N8N_EXPORT_WEBHOOK_URL` | e.g. `http://n8n:5678/webhook/decime/dictionary/export` |
| `N8N_IMPORT_WEBHOOK_URL` | e.g. `http://n8n:5678/webhook/decime/dictionary/import` |
| `N8N_AUTOMATION_KEY` | Shared secret; header `X-Decime-Automation-Key` |
| `GOOGLE_DICTIONARY_SPREADSHEET_ID` | Target spreadsheet for **export** (server-side only) |
| `DICTIONARY_SHEETS_JOB_TIMEOUT_MINUTES` | Default `30` — stale `queued`/`running` jobs → `failed` |
| `DICTIONARY_SHEETS_MAX_IMPORT_ROWS` | Default `5000` |

Attach API to the n8n Docker network (alias `decime-api`):

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.shared-vm.yml \
  -f docker-compose.n8n-net.yml up -d --build
```

n8n → API callbacks: `http://decime-api:8000/api/v1/...`  
Never forward the user JWT to n8n. Never put `N8N_AUTOMATION_KEY` in the browser / Next.js env.

### User-facing API (JWT)

| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `/api/v1/training/sheets/export` | `{ "list_id" }` | **202** `{ job_id, status }` after n8n accepts |
| POST | `/api/v1/training/sheets/import` | `{ list_id, source_spreadsheet_id, source_sheet_name }` | **202** |
| GET | `/api/v1/training/sheets/jobs/{job_id}` | — | Owner-only status + report |

- `user_id` and export `spreadsheet_id` come from the server session / config — not the client.
- Export sheet name: `user_<full user UUID>`.
- Concurrent second export for the same user → **409**.
- UI buttons are shown only in the **Russian** app language.
- Import UI accepts spreadsheet ID **or** Google Sheets URL (API extracts the ID).

Job statuses: `queued` → `running` → `completed` | `failed`.  
Report fields (import): `created`, `skipped`, `errors`, `partial`, optional `row_errors`.

### n8n → API (Header Auth)

Header: `X-Decime-Automation-Key: <N8N_AUTOMATION_KEY>`  
If the key is unset, these routes return **503**.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/integrations/n8n/jobs/{job_id}` | Job context including trusted `user_id` / `list_id` |
| POST | `/api/v1/integrations/n8n/jobs/{job_id}/import-row` | Body `{ source_row_number, spanish, russian }` → `created` \| `skipped_duplicate` \| `error` |
| POST | `/api/v1/integrations/n8n/jobs/{job_id}/complete` | Body `{ status, report, error_message? }` — idempotent; terminal jobs ignore late updates |

Import-row rules:

- User/list taken from the job — ignore any user_id in the sheet.
- One non-empty spanish cell → exactly one card (normalize path; not multi-extract add-to-vocab).
- Supplied russian kept; empty russian → AI generates translation.
- Source stats columns ignored; new cards start with zero review stats.
- Retries of the same `(job_id, source_row_number)` do not create a second card.
- Duplicates by server-computed `canonical_key` → `skipped_duplicate`.

### Backend → n8n webhook bodies

**Export**

```json
{
  "job_id": "UUID",
  "user_id": "UUID",
  "list_id": "UUID",
  "spreadsheet_id": "configured ID",
  "sheet_name": "user_USER_UUID"
}
```

**Import**

```json
{
  "job_id": "UUID",
  "source_spreadsheet_id": "ID",
  "source_sheet_name": "name"
}
```

Webhook response mode must acknowledge quickly (Respond to Webhook / “immediately”), then continue the workflow. Do not keep the Decime HTTP request open for the full Sheets sync.

### Export sheet format

Headers (row 1):

`item_id`, `canonical_key`, `spanish`, `russian`, `item_type`, `grammar`, `attempts`, `again`, `hard`, `good`, `easy`, `success_percent`, `hints`, `last_review_at`, `review_stage`, `next_review_at`

- `spanish` = `display_text`
- `russian` = `translations_ru` joined with `"; "`
- `grammar` = JSON text
- `attempts` = all attempts; grade buckets again/hard/good/easy
- success = **easy only**; `success_percent` = round(easy/attempts*100, 1) or blank if attempts=0
- `hints` = count of `used_hint`
- `last_review_at` = max attempt `created_at` (ISO UTC)
- Match/upsert Google rows by `item_id`
- Write values as text/RAW where possible (avoid formula injection)
- Do **not** delete sheet rows when a card is deleted in Decime
- Creating the tab if missing; one tab per user; exporting one list upserts into that shared tab

Example SQL (n8n Postgres node; placeholders from webhook body):

```sql
SELECT
  i.id::text AS item_id,
  i.canonical_key,
  i.display_text AS spanish,
  (
    SELECT string_agg(value, '; ')
    FROM jsonb_array_elements_text(i.translations_ru) AS value
  ) AS russian,
  i.item_type,
  i.grammar::text AS grammar,
  COALESCE(s.attempts, 0) AS attempts,
  COALESCE(s.again, 0) AS again,
  COALESCE(s.hard, 0) AS hard,
  COALESCE(s.good, 0) AS good,
  COALESCE(s.easy, 0) AS easy,
  CASE
    WHEN COALESCE(s.attempts, 0) = 0 THEN NULL
    ELSE ROUND((s.easy::numeric / s.attempts) * 100, 1)
  END AS success_percent,
  COALESCE(s.hints, 0) AS hints,
  s.last_review_at,
  i.review_stage,
  i.next_review_at
FROM training_items i
LEFT JOIN (
  SELECT
    a.item_id,
    a.user_id,
    COUNT(*) AS attempts,
    COUNT(*) FILTER (WHERE a.grade = 'again') AS again,
    COUNT(*) FILTER (WHERE a.grade = 'hard') AS hard,
    COUNT(*) FILTER (WHERE a.grade = 'good') AS good,
    COUNT(*) FILTER (WHERE a.grade = 'easy') AS easy,
    COUNT(*) FILTER (WHERE a.used_hint) AS hints,
    MAX(a.created_at) AS last_review_at
  FROM training_attempts a
  GROUP BY a.item_id, a.user_id
) s ON s.item_id = i.id AND s.user_id = i.user_id
WHERE i.user_id = $1::uuid
  AND i.list_id = $2::uuid
  AND i.status IN ('approved', 'known')
ORDER BY i.created_at;
```

Use a read-only DB role (e.g. `decime_n8n_reader`). Import **writes** only through the Decime API `import-row` endpoint.

### Manual workflow checklist

**Export (`Decime Export dictionary`) — required graph**

Dead-end IF branches cause n8n **Succeeded** while Decime stays `running`. Every path must end in `Complete export`.

```text
Webhook
→ Get job context          (GET /api/v1/integrations/n8n/jobs/{{job_id}})
→ Get spreadsheet tabs
→ Tab exists?

TRUE  → SQL query
FALSE → Create sheet → SQL query

SQL query
→ Has cards?

TRUE  → GS (upsert) → Export result → Complete export (completed)
FALSE → Empty export result → Complete export (completed)
```

**Create sheet** (Google Sheets → create sheet / add sheet):

- `spreadsheet_id`: `{{ $('Get job context').first().json.spreadsheet_id }}`
- sheet title: `{{ $('Get job context').first().json.sheet_name }}`
- After create, wire **always** back to **SQL query** (same node as TRUE branch).

**Complete export** (HTTP Request):

- `POST http://decime-api:8000/api/v1/integrations/n8n/jobs/{{ $('Get job context').first().json.job_id }}/complete`
- Header `X-Decime-Automation-Key`
- Body success: `{ "status": "completed", "report": { "exported_rows": …, "updated_rows": … } }`
- Empty dictionary: `{ "status": "completed", "report": { "exported_rows": 0, "message": "empty" } }`

**Error handling (n8n 2.40 — do not use blind Continue On Fail)**

1. **Error workflow** (recommended): new workflow `Decime Export dictionary - on error`
   - Trigger: **Error Trigger**
   - Code/Set: extract `job_id` from the failed execution’s webhook / Get job context item  
     (via n8n API `GET /api/v1/executions/{{ $json.execution.id }}?includeData=true` if needed)
   - HTTP Request → Decime `…/complete` with:
     ```json
     {
       "status": "failed",
       "report": {},
       "error_message": "{{ $json.execution.error.message }}"
     }
     ```
   - In **Decime Export dictionary** → Options → Settings → **Error workflow** = that workflow.
   - Activate both. Error Trigger runs only on **production** (webhook) executions that end in **Error**, not manual test runs.

2. **Critical nodes** (`Get job context`, `Get spreadsheet tabs`, `Create sheet`, `SQL query`, `GS`, `Export result`):
   - Leave **Continue On Fail** off so real failures mark the execution Error and fire the Error workflow.
   - Optional alternative: Settings → On Error → **Continue (using error output)** → wire error output to a shared **Complete export (failed)** HTTP node that uses  
     `job_id` from `$('Get job context')` and `error_message` from `$json.error.message` (or equivalent). Do **not** route error output into the success Complete path.

3. Never leave **Tab exists = false** or **Has cards = false** without a Complete call.

**Import**

1. Webhook POST `/webhook/decime/dictionary/import` + Header Auth  
2. Respond immediately  
3. `GET /integrations/n8n/jobs/{job_id}` for trusted `user_id`/`list_id`  
4. Read source spreadsheet/tab; for each non-empty data row call `import-row` sequentially  
5. `complete` with status/report (API overwrites created/skipped/errors from processed rows)
6. Same Error workflow pattern for unhandled node failures (pass `job_id` into `…/complete` with `status: failed`)

### Differences from the product brief

- Import spreadsheet field accepts URL or bare ID (API normalizes).
- Stale job timeout default 30 minutes (`DICTIONARY_SHEETS_JOB_TIMEOUT_MINUTES`).
- Active export serialized per user via unique partial index + **409**.
- Compose overlay file: `deploy/docker-compose.n8n-net.yml` (does not rewrite unrelated VM compose edits).

Until production export/import workflows are verified on the VM, do not claim full end-to-end readiness.

---

## Event types (from API)

| event_type | When |
|------------|------|
| `reply_generated` | After successful compose |
| `candidate_approved` | After training approve |
| `review_completed` | After review submit |
| `audio_transcribed` | After STT |
| `audio_generated` | After TTS |
| `error_occurred` | API errors on key routes |

## Example: daily Telegram report

```sql
SELECT event_type, COUNT(*) AS count
FROM event_log
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY event_type
ORDER BY count DESC;
```

n8n workflow:

1. **Schedule** — daily 09:00 UTC
2. **Postgres** — run query above
3. **Telegram** — send formatted summary to admin chat

## Example: inactive users (7 days)

```sql
SELECT u.email, MAX(e.created_at) AS last_event
FROM app_users u
LEFT JOIN event_log e ON e.user_id = u.id
GROUP BY u.email
HAVING MAX(e.created_at) < NOW() - INTERVAL '7 days'
   OR MAX(e.created_at) IS NULL;
```

## PostHog bridge (optional)

n8n **HTTP Request** node can forward selected `event_log` rows to PostHog capture API — keeps SDK out of the FastAPI runtime.

## Backup workflow

1. Schedule nightly
2. `pg_dump` via Execute Command or Postgres node
3. Upload to S3 / Backblaze

n8n itself is not added to `docker-compose.yml` by default; use the external `decime_n8n` network overlay when n8n already runs on the VM.
