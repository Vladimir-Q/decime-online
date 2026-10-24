# Decime UY — Technical Brief (Next Phase)

**Version:** 0.3  
**Date:** 2026-06-23

---

# Architecture philosophy

FastAPI remains the runtime core.

n8n is not part of runtime logic.

Runtime:

```text
Next.js
↓
FastAPI
↓
Services
↓
Providers
```

Background automation:

```text
n8n
```

for:

- analytics;
- notifications;
- backups;
- monitoring;
- reporting.

---

# Technical priorities

Priority order:

```text
P0
Persistence

P1
Android QA

P2
VM deployment

P3
User isolation

P4
Analytics

P5
n8n infrastructure
```

---

# Phase A — Persistence

Current problem:

```text
MemoryTrainingRepository
MemoryHistoryRepository
```

lose data on restart.

Goal:

Move to persistent storage.

Preferred options:

### Option 1

PostgreSQL

### Option 2

Supabase Postgres

### Option 3

SQLite

for single-user deployment.

---

Acceptance criteria:

```text
Restart API
↓
History survives

Training survives

SRS survives

Extractions survive
```

---

# Phase B — User isolation

Current issue:

Multiple users share memory repositories.

Goal:

All entities become user-scoped.

Must filter by:

```python
user_id
```

for:

- training_items;
- lists;
- review attempts;
- history;
- audio;
- transcripts;
- reply requests.

---

# Phase C — VM deployment

Target:

Single VM.

Components:

```text
Nginx
↓
FastAPI
↓
PostgreSQL
```

Optional:

```text
Docker Compose
```

Authentication:

```text
AUTH_ENABLED=true
```

HTTPS required.

---

# Phase D — Android QA

Complete real device validation.

Scenarios:

## Text share

WhatsApp

↓

Decime

↓

Reply

↓

Share back

---

## Voice note

WhatsApp

↓

Audio share

↓

STT

↓

Reply

↓

TTS

↓

WhatsApp

---

# Phase E — Analytics

Recommended:

PostHog.

Track events:

```python
reply_generated

candidate_approved

review_completed

audio_transcribed

audio_generated

error_occurred
```

---

# Phase F — n8n

n8n is not responsible for:

- compose;
- STT;
- TTS;
- extraction;
- review scheduling.

n8n responsibilities:

---

## Monitoring

Sentry

↓

Telegram

---

## Daily report

OpenAI cost

Users

Errors

Replies

↓

Telegram

---

## Inactive users

7 days inactive

↓

Email

---

## Backup

PostgreSQL dump

↓

Cloud storage

---

## Batch evaluation

Random conversations

↓

GPT evaluation

↓

Quality score

---

## Admin bot

Telegram

Commands:

```text
/stats
/users
/errors
/cost
```

---

# Future architecture

```text
                Next.js
                    ↓
                FastAPI
                    ↓
    --------------------------------
    compose
    audio
    training
    SRS
    history
    providers
    --------------------------------
                    ↓
               PostgreSQL

Background layer

n8n
    ↓
analytics
monitoring
backups
notifications
quality evaluation
admin tools
```

---

# Explicitly out of scope

Not planned:

- LangGraph;
- CrewAI;
- MCP orchestration;
- vector databases;
- realtime voice;
- autonomous agents;
- Twilio;
- RAG.

---

# Technical success metric

The next phase is successful when:

```text
The application can run for months

without losing user data

and without manual intervention.
```
