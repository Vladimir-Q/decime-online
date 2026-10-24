# Decime UY — Technical Task for Cursor

**Purpose:** implement the next Decime UY private VM alpha milestone.

**Audience:** Cursor / AI coding agent.

**Repository:** current monorepo at `c:\CODG\decime`.

---

## 1. Goal

Prepare Decime UY for a private multi-user VM deployment with Android phone testing.

The product is now:

```text
Context-aware communication translator for Uruguay
+ lightweight training from generated/translated material
```

Do not treat this milestone as a feature expansion. It is a refactor + productionization step.

---

## 2. Current known state

The project currently has:

- Next.js web app.
- Capacitor Android APK.
- FastAPI backend.
- Android share intents for `text/plain` and `audio/*`.
- Native HTTP plugin.
- JWT auth partially implemented.
- Admin users page.
- Quick Reply, Compose, Audio, Training, Review, History screens.
- Memory repositories for training/history.
- SQLite users when auth is enabled.
- Local audio files on disk.
- Optional Supabase history only.
- LLM/STT/TTS provider abstraction.
- OpenAI/Ollama/faster-whisper/Orpheus provider options.

Known blockers:

- Training/history are in-memory.
- Business data is not isolated by `user_id`.
- Auth E2E on Android is not complete.
- Current UI is split into Quick Reply / Compose / Audio, but product direction now requires Assistant / Live.
- `DELETE /api/v1/history` currently clears too much.
- VM deployment is not complete.

---

# 3. Hard scope

## Implement

```text
Postgres runtime persistence
strict user isolation
AUTH_ENABLED=true production mode
invite-only users
web-only admin
conversation sessions
Assistant screen
Live screen
Formal/Friendly/Simple variants
adverb training item type
Android production API URL
Docker/Caddy/Postgres VM deployment
manual backup
basic LocaleCriticUY for obvious non-UY output
QA docs
```

## Do not implement

```text
Twilio
Meta WhatsApp API
WhatsApp bot
Palabra
Realtime speech
Multi-region
Payments
Public registration
Pronunciation scoring
Expression/idiom extraction
Full offline mode
Admin in Android
```

---

# 4. Architecture target

## Runtime target

```text
Android APK / Web browser
        ↓ HTTPS
Caddy reverse proxy
        ↓
FastAPI API
        ↓
Postgres
        ↓
audio storage volume
        ↓
local AI providers:
  Ollama
  faster-whisper
  Orpheus
```

OpenAI may remain as a diagnostic fallback, but the intended VM runtime should prefer local providers.

---

# 5. Backend data model changes

## 5.1 Add conversation sessions

Create runtime persistence for:

```text
conversation_sessions
conversation_turns
```

### conversation_sessions

Required fields:

```text
id uuid primary key
user_id uuid not null
status text -- active / closed / deleted
locale_variant text default es-UY-montevideo
created_at timestamptz
updated_at timestamptz
cleared_at timestamptz nullable
```

### conversation_turns

Required fields:

```text
id uuid primary key
session_id uuid not null
user_id uuid not null
turn_type text
  -- incoming_text
  -- incoming_audio_transcript
  -- user_reply_intent
  -- generated_reply
  -- edited_reply
  -- translation
source_language text nullable
target_language text nullable
original_text text nullable
translated_text text nullable
audio_file_id uuid nullable
reply_variant text nullable
  -- formal / friendly / simple
metadata jsonb
created_at timestamptz
```

### Rules

- All turns must belong to current user.
- Current active session is used as context for Assistant.
- Start new conversation clears/deletes active session context for current user.
- Training items created from old sessions must remain.

---

## 5.2 Migrate all business data to Postgres

Replace:

```text
MemoryTrainingRepository
MemoryHistoryRepository
SQLite auth users
```

with Postgres-backed repositories.

Use current migrations if possible, but adjust them to current runtime needs.

### Tables requiring `user_id`

Every business entity must include and enforce `user_id`:

```text
conversation_sessions
conversation_turns
reply_requests
reply_outputs
training_lists
training_items
extraction_runs
training_attempts
audio_files
transcripts
event_log
```

### User isolation rule

Every repository method must receive or derive `current_user.id`.

Every SELECT/INSERT/UPDATE/DELETE must be scoped by `user_id`.

Admin user-management endpoints must not expose user content.

---

## 5.3 Auth users in Postgres

Move auth from SQLite to Postgres.

Required table:

```text
app_users
```

Required fields:

```text
id uuid primary key
email text unique not null
password_hash text not null
role text not null -- admin / user
is_active boolean not null default true
created_at timestamptz
updated_at timestamptz
last_login_at timestamptz nullable
```

### Auth production settings

```env
AUTH_ENABLED=true
ALLOW_REGISTRATION=false
AUTH_JWT_SECRET=<long-random-secret>
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=<reasonable long private alpha value>
```

### Admin rules

- Admin can create users.
- Admin can disable users.
- Admin can reset/change passwords.
- Admin is not a normal product user.
- Android should not show admin UI.

---

# 6. API changes

Preserve current endpoints where possible.

Add or adjust endpoints as needed.

## 6.1 Assistant endpoints

Preferred API shape:

```text
GET    /api/v1/assistant/session
POST   /api/v1/assistant/session/new
GET    /api/v1/assistant/session/{session_id}/turns
POST   /api/v1/assistant/incoming-text
POST   /api/v1/assistant/incoming-audio
POST   /api/v1/assistant/reply
PATCH  /api/v1/assistant/reply/{turn_id}
```

### incoming-text

Input:

```json
{
  "text": "...",
  "source_language": "auto|es|ru|en",
  "context_mode": "chat"
}
```

Output:

```json
{
  "session_id": "...",
  "turn_id": "...",
  "original_text": "...",
  "source_language": "es",
  "translation_ru": "...",
  "translation_en": "...",
  "used_context": true
}
```

### incoming-audio

Accept multipart audio.

Output:

```json
{
  "session_id": "...",
  "audio_file_id": "...",
  "transcript": "...",
  "source_language": "es",
  "translation_ru": "...",
  "translation_en": "..."
}
```

### reply

Input:

```json
{
  "reply_intent_text": "...",
  "source_language": "ru|en|auto",
  "preserve_number_format": true
}
```

Output:

```json
{
  "session_id": "...",
  "variants": {
    "formal": {
      "text": "...",
      "notes": []
    },
    "friendly": {
      "text": "...",
      "notes": []
    },
    "simple": {
      "text": "...",
      "notes": []
    }
  },
  "locale_variant": "es-UY-montevideo"
}
```

Formal must appear first in frontend ordering.

## 6.2 Live endpoints

Preferred:

```text
POST /api/v1/live/translate-text
POST /api/v1/live/translate-audio
```

Live output must be one translation, not variants.

Input may be:

```text
RU/EN → ES
ES → RU/EN
```

Default style for RU/EN → ES:

```text
polite
brief
sufficiently formal
es-UY-montevideo
```

## 6.3 Training endpoints

Keep existing endpoints if compatible:

```text
POST /api/v1/training/extract-candidates
POST /api/v1/training/approve-candidates
GET  /api/v1/training/lists
GET  /api/v1/training/items
GET  /api/v1/training/review/next
POST /api/v1/training/review/submit
```

Add:

```text
DELETE /api/v1/training/items/{item_id}
DELETE /api/v1/training/lists/{list_id}
```

Support item type:

```text
adverb
```

Remove any behavior that auto-adds infinitives from verb forms.

## 6.4 Destructive endpoints

Fix current dangerous behavior.

Required:

```text
DELETE /api/v1/history
```

must delete only history if retained.

Add explicit endpoints:

```text
DELETE /api/v1/audio/cache
POST   /api/v1/training/reset
DELETE /api/v1/assistant/session/current
```

Do not delete training when clearing history/conversation.

---

# 7. Prompt/schema changes

## 7.1 Assistant reply generation prompt

Update prompt so it generates exactly:

```text
formal
friendly
simple
```

No recommended/short/more formal variants.

Rules:

- Target locale: es-UY-montevideo.
- Preserve number format.
- Use current conversation context.
- Accept mixed RU/EN with Spanish terms.
- If the user inserts a Spanish word into Russian/English text, preserve that term if semantically appropriate.
- Avoid Spain-specific vocabulary and grammar.
- Avoid over-slangy Argentine output.
- Keep output natural for Uruguay.

## 7.2 Incoming translation prompt

Remove “what they want” block from default output.

Return:

```text
original/transcript
translation_ru
translation_en optional
optional_explanation behind button
```

## 7.3 Live prompt

Generate one output only.

RU/EN → ES:

```text
polite
brief
sufficiently formal
es-UY-montevideo
```

ES → RU/EN:

```text
clear direct translation
```

## 7.4 Training extraction prompt

Update to support:

```text
noun
adjective
adverb
verb_form
verb_infinitive
```

Do not extract:

```text
expression
sentence_pattern
idiom
collocation
full_phrase
```

Verb forms:

- include display form with pronoun;
- include lemma;
- include tense/mood/person/number;
- include voseo flag;
- include governance if known;
- do not auto-add infinitive.

---

# 8. Frontend refactor

## 8.1 Navigation

### Mobile nav

```text
Assistant
Live
Training
Settings
```

### Web nav

```text
Assistant
Live
Training
Review
History
Settings
Admin
```

Admin must be hidden from Android.

## 8.2 Replace/supersede routes

Existing:

```text
/app/quick-reply
/app/compose
/app/audio
```

New:

```text
/app/assistant
/app/live
```

Do not necessarily delete old routes immediately, but remove them from primary nav and route mobile start to `/app/assistant`.

## 8.3 Assistant UI

Assistant must include:

- active conversation panel;
- Start new conversation button;
- input area:
  - paste text;
  - shared text;
  - upload audio;
  - record audio;
- translation area;
- reply intent input;
- Generate reply button;
- Formal/Friendly/Simple variant cards;
- per-card actions:
  - Edit;
  - Copy;
  - Share;
  - Play;
  - Add to training;
- optional Explain button.

## 8.4 Live UI

Live must include:

- large microphone button;
- text fallback input;
- direction auto-detect:
  - RU/EN → ES;
  - ES → RU/EN;
- one output card;
- Play;
- Copy;
- optional Share;
- optional Add to training;
- no variant selector.

## 8.5 History UI

History should reflect conversation/session model.

Do not expose “clear history” in a way that deletes training.

---

# 9. Android changes

## 9.1 Production API URL

Android APK should use one production API URL by default.

Remove LAN scan from primary user flow.

Settings override may remain in dev/settings.

## 9.2 App start

Start route:

```text
/app/assistant
```

## 9.3 Share-in

When receiving:

```text
text/plain
```

open Assistant with shared text as incoming content.

When receiving:

```text
audio/*
```

open Assistant and trigger transcription/translation flow.

## 9.4 Share-out

Use current Capacitor/Android share support.

If easy, add a specific “Share to WhatsApp” action with fallback to generic share.

Never auto-send messages.

## 9.5 Auth

Android must support:

- login;
- token persistence;
- logout;
- invalid token redirect to login;
- share intent after login;
- shared payload should not be lost during login if feasible.

---

# 10. VM deployment

## 10.1 Target stack

Use Docker Compose.

Services:

```text
caddy
api
web
postgres
ollama
faster-whisper service or API-integrated worker
orpheus
```

If faster-whisper and Orpheus are already integrated differently, keep current provider shape but document it.

## 10.2 Files to add

```text
apps/api/Dockerfile
apps/web/Dockerfile or static export deployment
docker-compose.prod.yml
deploy/Caddyfile
.env.production.example
scripts/deploy_vm.sh
scripts/backup_postgres.sh
scripts/restore_postgres.sh optional
docs/vm_deploy.md
docs/production_env.md
```

## 10.3 Production env defaults

```env
AUTH_ENABLED=true
ALLOW_REGISTRATION=false
DATABASE_URL=postgresql://...
AUDIO_STORAGE_PATH=/app/data/audio

LLM_PROVIDER=ollama
STT_PROVIDER=faster_whisper
TTS_PROVIDER=orpheus

OPENAI_FALLBACK_ENABLED=true
```

## 10.4 Manual backup

Implement a manual backup script for:

- Postgres dump;
- audio storage volume.

Do not build automated backup scheduling unless easy.

---

# 11. Tests

## 11.1 Backend tests

Add tests for:

- Postgres repository persistence;
- user A cannot see user B conversation sessions;
- user A cannot see user B training items;
- user A cannot fetch user B audio file;
- history deletion does not delete training;
- start new conversation clears only active context;
- training item delete works;
- adverb candidate extraction supported;
- verb form does not auto-create infinitive;
- protected routes require JWT when `AUTH_ENABLED=true`.

## 11.2 AI contract tests

Use fake providers where needed, but add schema/contract tests for:

- Assistant variants exactly Formal/Friendly/Simple.
- Formal first in UI ordering.
- number format preserved.
- no “what they want” block in default translation.
- Live returns one output only.
- training extraction returns allowed item types only.

## 11.3 LocaleCriticUY

Implement minimal `LocaleCriticUY`.

It should flag obvious non-UY output:

```text
vosotros
vosotras
podéis
tenéis
vale
móvil
ordenador
coger in Spain-specific sense
```

Output:

```text
ok
needs_review
probably_not_uy
```

Do not overcomplicate.

Add 20–30 golden cases later or start with a small test set now.

## 11.4 Android E2E

Update E2E scripts/checklist for:

- login;
- share text into Assistant;
- share audio into Assistant;
- generate Formal/Friendly/Simple;
- share Formal back out;
- start new conversation;
- add to training;
- review item;
- app restart;
- token persists.

---

# 12. Documentation updates

Update or create:

```text
docs/product_brief.md
docs/development_brief.md
docs/product_status_report.md
docs/technical_status_report.md
docs/vm_deploy.md
docs/android_setup.md
docs/qa_checklist.md
docs/out_of_scope.md
docs/project_state.md
```

Docs must explicitly say:

```text
Twilio, Meta WhatsApp API, WhatsApp bot, Palabra are out of active roadmap.
```

---

# 13. Implementation order

Follow this order.

## Phase 1 — Docs and contracts

- Update docs to reflect new product direction.
- Add API contract stubs for Assistant, Live, sessions.
- Add DB migration plan.

## Phase 2 — Persistence/auth foundation

- Add Postgres runtime repositories.
- Move auth users to Postgres.
- Add user_id scoping everywhere.
- Add tests.

## Phase 3 — Conversation sessions

- Add session/turn models.
- Implement Assistant endpoints.
- Implement Start new conversation.

## Phase 4 — UI refactor

- Create Assistant screen.
- Create Live screen.
- Update nav.
- Hide old Quick Reply/Compose/Audio from primary nav.
- Update Android start route.

## Phase 5 — Training changes

- Add adverb item type.
- Update extraction prompt/schema.
- Add delete item/list.
- Ensure no auto-infinitive behavior.

## Phase 6 — VM deployment

- Docker Compose.
- Caddy.
- Postgres volume.
- AI provider services.
- backup scripts.
- env docs.

## Phase 7 — Android production testing

- Production API URL.
- Auth E2E.
- Share-in/share-out E2E.
- Phone QA.

## Phase 8 — Locale quality gate

- Add LocaleCriticUY.
- Add golden cases.
- Add QA checklist.

---

# 14. Completion definition

This task is complete only when:

- Decime runs on VM over HTTPS.
- Android APK connects to VM by default.
- User login works on Android.
- Up to 5 invited users can use the service without seeing each other’s data.
- Assistant replaces Quick Reply/Compose/Audio as the main flow.
- Live screen exists and works with microphone/text.
- Formal/Friendly/Simple variants are generated.
- Current conversation context works.
- Start new conversation clears active context.
- Training persists after API restart.
- History deletion does not delete training.
- Admin is web-only.
- Twilio/Palabra remain out of roadmap.
- QA checklist is updated and run.

---

# 15. Cursor instruction

Work carefully and incrementally.

Do not rewrite the whole project unless necessary.

Prefer small commits/changes by phase.

After each phase:

- run backend tests;
- run frontend build;
- update docs;
- list known remaining issues.

If any existing implementation conflicts with this task, preserve working behavior until the replacement is ready.

