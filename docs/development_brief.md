# Decime UY — Development Brief for Cursor

**Version:** 0.2  
**Date:** 2026-06-23 (original 2026-05-16)  
**Owner:** Vladimir Karataev  
**Goal:** Build a solo-developer MVP with AI coding assistance in Cursor  
**Product:** Decime UY — Uruguayan Spanish Communication Copilot + Personal Phrase Trainer

> **Current runtime (2026-10):** Text LLM is **LangChain + OpenAI / OpenAI-compatible only** — no Ollama text path, no `LLM_ORCHESTRATOR=legacy`. Product UI uses **one** Spanish reply plus tone (not multi-variant drafts). Prefer [project_state.md](project_state.md) and [../README.md](../README.md) for “how it runs today”; this brief remains the broader design context and may describe earlier MVP wording (variants, optional providers).

---

## 1. Development objective

Build an MVP that proves the core loop:

```text
RU/EN/ES text or audio input
  → context-aware Uruguay/Montevideo Spanish reply or explanation
  → audio pronunciation
  → Add to training
  → extract atomic learning items
  → user approves
  → training list and review queue
```

This development brief is written to be placed directly into the repository and used as Cursor context.

Recommended path:

```text
docs/product_brief.md
docs/development_brief.md
docs/api_contracts.md
docs/prompt_contracts.md
docs/database_schema.sql
docs/mvp_tasks.md
```

---

## 2. High-level architecture

Recommended MVP architecture:

```text
Next.js PWA frontend
        ↓
FastAPI backend
        ↓
AI service layer
        ↓
OpenAI + local Whisper / Orpheus (see out_of_scope.md — no Palabra)
        ↓
Supabase Postgres + Supabase Storage
```

### Why this stack

- **Next.js / React / TypeScript** for mobile-first PWA and fast UI iteration.
- **FastAPI / Python** because the existing FL-learning project is Python-based and the user already has OpenAI/TTS experimentation in Python.
- **Supabase** for managed Postgres, auth and storage in one MVP-friendly service; Supabase docs describe Database/Postgres, Auth and Storage as core services.
- **OpenAI** for structured text generation and optional cloud STT/TTS.
- **Local** Whisper STT and Orpheus TTS for personal/VM setups.
- **WhatsApp** via Share/copy only — **not** Twilio (see [out_of_scope.md](out_of_scope.md)).

---

## 3. Development principles

1. **Build deterministic workflows, not autonomous agents first.**
   - “Agents” should be modules/functions with clear inputs and outputs.
   - Avoid autonomous planning until the base loop is stable.

2. **Use structured outputs for LLM responses.**
   - The backend should parse typed JSON, not fragile free text.
   - OpenAI Structured Outputs are designed for schema-constrained output and type-safe parsing.

3. **Keep providers replaceable.**
   - STT, TTS and LLM calls must go through interfaces.
   - Text LLM: OpenAI / OpenAI-compatible (LangChain). Speech: faster-whisper, Orpheus (+ Ollama for voice model), optional OpenAI STT/TTS, fake (tests).
   - **Not planned:** Palabra, Twilio — [out_of_scope.md](out_of_scope.md).

4. **Do not overbuild WhatsApp integration.**
   - Use copy, upload, and Android Share — no messaging API bots.

5. **Make every AI result inspectable.**
   - Save prompts, input, output JSON, model name, latency, errors and cost estimates where possible.

6. **Never auto-add training items silently.**
   - Always show candidates and let the user approve.

7. **Treat `surface_text` as the learning object.**
   - `voy` and `ir` are different items.
   - `vos podés` and `poder` are different items.

8. **Start with atomic training items.**
   - Nouns, adjectives, verb forms, infinitives.
   - Full expressions later.

---

## 4. Recommended repository structure

```text
decime/
  README.md
  .env.example
  docs/
    README.md              ← documentation index
    project_state.md       ← current snapshot

  apps/
    web/                   Next.js 15 + Capacitor Android
    api/
      src/decime_api/
        main.py
        config.py
        auth/
        db/
        routers/
          auth.py
          compose.py
          incoming.py
          audio.py
          training.py
          history.py
        services/
          ai/                LLM, STT, TTS providers
          auth/              JWT, passwords
          compose/
          training/
          storage/
        schemas/
        prompts/
        tests/

  supabase/migrations/
  scripts/                   start_local.sh, android_e2e, create_admin
```

For the existing FL-learning project, keep reusable code as reference, but do not let old Gradio UI define the new product architecture. Reuse ideas/services, not the old UI shape.

---

## 5. Environment variables

`.env.example`:

```bash
# App
APP_ENV=local
APP_NAME=Decime UY
APP_LOCALE_DEFAULT=es-UY-montevideo

# OpenAI
OPENAI_API_KEY=
OPENAI_TEXT_MODEL=gpt-6-luna
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET_AUDIO=audio

# Backend
API_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:3000

# Auth (VM — off by default locally)
AUTH_ENABLED=false
AUTH_JWT_SECRET=
AUTH_DATABASE_PATH=data/decime.db

# AI providers (see .env.example for full list)
LLM_PROVIDER=openai|fake
STT_PROVIDER=faster_whisper|openai|ollama|fake
TTS_PROVIDER=orpheus|openai|fake

# Twilio / Palabra — out of scope (docs/out_of_scope.md)
```

Note from existing FL-learning experiments: keep `load_dotenv(override=True)` behavior if local `.env` switching is useful, but do not commit secrets.

---

## 6. Services and models

## 6.1 Text generation / reply composition

Use OpenAI Responses API or current OpenAI text generation endpoint with structured output.

Primary tasks:

- context-aware reply generation;
- translation RU/EN → es-UY;
- explanation ES → RU/EN;
- extraction of training candidates;
- optional locale validation.

Use typed schemas in Pydantic.

## 6.2 STT

Default:

```text
gpt-4o-mini-transcribe
```

Quality mode:

```text
gpt-4o-transcribe
```

The OpenAI Speech-to-Text docs state that `gpt-4o-transcribe` and `gpt-4o-mini-transcribe` support JSON or plain text outputs.

## 6.3 TTS

Default:

```text
gpt-4o-mini-tts
```

Prompt the model with instructions like:

```text
Speak in natural Uruguayan Spanish from Montevideo. Use a clear, neutral, not exaggerated Rioplatense tone. Moderate speed. Suitable for a learner to imitate.
```

The OpenAI TTS docs state that `gpt-4o-mini-tts` can be prompted to control accent, intonation, speed and tone.

## 6.4 Realtime speech

Not MVP. Keep for later.

Existing FL-learning experiments with Realtime WebSocket can be preserved as research, but the MVP should use request-response audio:

```text
record/upload → transcribe → compose → synthesize → play/cache
```

## 6.5 Third-party speech (Palabra)

**Out of scope.** Provider interfaces (`STTProvider`, `TTSProvider`) are implemented for OpenAI, Ollama, faster-whisper, and Orpheus only. See [out_of_scope.md](out_of_scope.md).

---

## 7. Backend API endpoints

Base prefix:

```text
/api/v1
```

Public: `GET /health`, `GET/POST /api/v1/auth/*` (see [vm_auth.md](vm_auth.md)).

Protected when `AUTH_ENABLED=true`: compose, incoming, history, audio, training.

## 7.0 Understand incoming (Quick Reply)

```http
POST /api/v1/incoming/understand-text
```

Translates incoming Spanish to RU/EN. See [api_contracts.md](api_contracts.md).

## 7.1 Translate to es-UY

```http
POST /api/v1/translate/text
```

Request:

```json
{
  "source_language": "auto",
  "source_text": "Я хочу уточнить, можно ли оплатить картой.",
  "context": {
    "target_locale": "es-UY-montevideo",
    "channel": "whatsapp_text",
    "situation": "shop_payment",
    "tone": "polite_neutral",
    "user_level": "A2"
  },
  "output_options": {
    "include_variants": true,
    "include_explanation": true,
    "include_training_preview": false
  }
}
```

Response:

```json
{
  "request_id": "uuid",
  "target_locale": "es-UY-montevideo",
  "dialect_stamp": "🇺🇾 Uruguay · Montevideo · WhatsApp · neutral amable · A2-friendly",
  "intent_summary_ru": "Пользователь хочет вежливо уточнить, можно ли оплатить картой.",
  "recommended_reply": "Hola, quería consultar si se puede pagar con tarjeta.",
  "simple_reply": "Hola, ¿se puede pagar con tarjeta?",
  "short_reply": "¿Se puede pagar con tarjeta?",
  "more_formal_reply": "Hola, quisiera consultar si es posible pagar con tarjeta.",
  "notes_ru": [
    "quería consultar звучит мягко и естественно",
    "se puede pagar — обычная нейтральная конструкция"
  ],
  "warnings": [],
  "can_add_to_training": true
}
```

## 7.2 Transcribe audio

```http
POST /api/v1/audio/transcribe
```

Form-data:

```text
file: audio file
language_hint: auto | ru | en | es
source_type: user_voice | whatsapp_audio
```

Response:

```json
{
  "audio_id": "uuid",
  "transcript_id": "uuid",
  "language": "es",
  "transcript": "¿Me podés mandar la factura?",
  "confidence_notes": [],
  "duration_ms": 3200
}
```

## 7.3 Synthesize audio

```http
POST /api/v1/audio/synthesize
```

Request:

```json
{
  "text": "¿Me podés mandar la factura?",
  "locale": "es-UY-montevideo",
  "mode": "training_reference",
  "speed": "normal"
}
```

Response:

```json
{
  "audio_id": "uuid",
  "audio_url": "https://...",
  "cached": false
}
```

## 7.4 Extract training candidates

```http
POST /api/v1/training/extract-candidates
```

Request:

```json
{
  "source_type": "generated_reply",
  "source_language": "ru",
  "source_original_text": "Я хочу уточнить, можно ли оплатить картой.",
  "spanish_text": "Quería consultar si se puede pagar con tarjeta.",
  "target_locale": "es-UY-montevideo",
  "user_level": "A2",
  "list_id": "uuid-or-null",
  "candidate_types": ["noun", "adjective", "verb_form", "verb_infinitive"]
}
```

Response:

```json
{
  "extraction_id": "uuid",
  "candidates": [
    {
      "candidate_id": "temp-id-1",
      "item_type": "verb_form",
      "surface_text": "quería",
      "display_text": "yo quería",
      "lemma": "querer",
      "translations_ru": ["я хотел", "я хотела"],
      "translations_en": ["I wanted"],
      "context_translation_ru": "я хотел/хотела, вежливая смягчающая форма",
      "grammar": {
        "pronoun": "yo",
        "person": 1,
        "number": "singular",
        "tense": "pretérito imperfecto",
        "mood": "indicativo",
        "voseo": false
      },
      "governance": ["querer + infinitivo"],
      "example_es": "Quería consultar si se puede pagar con tarjeta.",
      "example_ru": "Я хотел(а) уточнить, можно ли оплатить картой.",
      "status_hint": "new"
    },
    {
      "candidate_id": "temp-id-2",
      "item_type": "noun",
      "surface_text": "la tarjeta",
      "display_text": "la tarjeta",
      "lemma": "tarjeta",
      "translations_ru": ["карта"],
      "translations_en": ["card"],
      "grammar": {
        "article": "la",
        "gender": "feminine",
        "number": "singular"
      },
      "example_es": "Quería consultar si se puede pagar con tarjeta.",
      "status_hint": "new"
    }
  ]
}
```

## 7.5 Approve candidates

```http
POST /api/v1/training/approve-candidates
```

Request:

```json
{
  "list_id": "uuid",
  "extraction_id": "uuid",
  "approved_candidate_ids": ["temp-id-1", "temp-id-2"],
  "generate_audio": true
}
```

Response:

```json
{
  "created_items": [
    {"item_id": "uuid", "surface_text": "yo quería", "audio_status": "queued"},
    {"item_id": "uuid", "surface_text": "la tarjeta", "audio_status": "queued"}
  ],
  "skipped_duplicates": []
}
```

## 7.6 Training review

```http
GET /api/v1/training/review/next?list_id=uuid&limit=20
```

Response:

```json
{
  "items": [
    {
      "item_id": "uuid",
      "item_type": "verb_form",
      "display_text": "vos podés",
      "prompt_ru": "ты можешь / можешь",
      "prompt_en": "you can",
      "audio_url": "https://...",
      "review_modes": ["ru_to_es", "es_to_ru", "audio_to_meaning", "grammar_prompt"]
    }
  ]
}
```

Submit review:

```http
POST /api/v1/training/review/submit
```

Request:

```json
{
  "item_id": "uuid",
  "review_mode": "ru_to_es",
  "grade": "good",
  "response_latency_ms": 4100,
  "used_hint": false
}
```

---

## 8. Database schema draft

Use Supabase/Postgres.

```sql
create table profiles (
  id uuid primary key,
  email text,
  display_name text,
  native_language text default 'ru',
  secondary_language text default 'en',
  target_locale text default 'es-UY-montevideo',
  user_level text default 'A2',
  created_at timestamptz default now()
);

create table locale_variants (
  id text primary key,
  country text not null,
  region text,
  label text not null,
  is_active boolean default true,
  default_formality text,
  pronoun_policy text,
  notes text
);

create table situations (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  label_ru text not null,
  label_en text not null,
  label_es text,
  default_channel text,
  created_at timestamptz default now()
);

create table audio_files (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  source_type text not null,
  storage_path text not null,
  public_url text,
  mime_type text,
  duration_ms int,
  provider text,
  model text,
  voice text,
  text_hash text,
  created_at timestamptz default now()
);

create table transcripts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  audio_id uuid references audio_files(id),
  language text,
  transcript text not null,
  provider text,
  model text,
  raw_payload jsonb,
  created_at timestamptz default now()
);

create table reply_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  source_language text,
  source_text text,
  incoming_text text,
  incoming_audio_id uuid references audio_files(id),
  transcript_id uuid references transcripts(id),
  situation_id uuid references situations(id),
  channel text,
  tone text,
  target_locale text default 'es-UY-montevideo',
  user_level text,
  source_type text,
  created_at timestamptz default now()
);

create table reply_outputs (
  id uuid primary key default gen_random_uuid(),
  request_id uuid references reply_requests(id),
  recommended_reply text not null,
  simple_reply text,
  short_reply text,
  more_formal_reply text,
  intent_summary_ru text,
  intent_summary_en text,
  notes_ru jsonb,
  notes_en jsonb,
  warnings jsonb,
  dialect_stamp text,
  raw_json jsonb,
  provider text,
  model text,
  latency_ms int,
  created_at timestamptz default now()
);

create table training_lists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  name text not null,
  source text default 'manual',
  locale_variant text references locale_variants(id),
  is_base boolean default false,
  created_at timestamptz default now()
);

create table training_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  list_id uuid references training_lists(id),

  item_type text not null,
  -- noun / adjective / verb_form / verb_infinitive

  surface_text text not null,
  display_text text not null,
  lemma text,
  locale_variant text references locale_variants(id),

  translations_ru jsonb not null default '[]'::jsonb,
  translations_en jsonb not null default '[]'::jsonb,
  context_translation_ru text,
  context_translation_en text,

  grammar jsonb not null default '{}'::jsonb,
  governance jsonb not null default '[]'::jsonb,

  example_es text,
  example_ru text,
  example_en text,

  audio_id uuid references audio_files(id),

  source_type text,
  source_language text,
  source_original_text text,
  source_transcript_id uuid references transcripts(id),
  source_reply_output_id uuid references reply_outputs(id),

  status text default 'approved',
  -- candidate / approved / skipped / known / ignored

  canonical_key text,
  next_review_at timestamptz default now(),
  review_stage int default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create unique index training_items_user_canonical_key_idx
  on training_items(user_id, canonical_key)
  where canonical_key is not null and status in ('approved', 'known');

create table extraction_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  source_type text not null,
  source_language text,
  source_original_text text,
  spanish_text text not null,
  target_locale text default 'es-UY-montevideo',
  raw_candidates jsonb,
  provider text,
  model text,
  created_at timestamptz default now()
);

create table training_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  item_id uuid references training_items(id),
  review_mode text not null,
  grade text not null,
  response_latency_ms int,
  used_hint boolean default false,
  user_answer_text text,
  attempt_audio_id uuid references audio_files(id),
  transcript_id uuid references transcripts(id),
  created_at timestamptz default now()
);

create table event_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);
```

Seed `locale_variants`:

```sql
insert into locale_variants(id, country, region, label, default_formality, pronoun_policy, notes)
values
('es-UY-montevideo', 'Uruguay', 'Montevideo', 'Uruguayan Spanish / Montevideo', 'polite_neutral', 'vos default where natural; ustedes plural', 'MVP default locale. Avoid Spain-specific output and excessive Buenos Aires slang.');
```

---

## 9. Canonical keys and deduplication

Canonical key must not collapse forms into lemmas.

Examples:

```text
es-UY-montevideo|noun|la factura|feminine|singular|factura
es-UY-montevideo|verb_form|podés|poder|vos|presente|indicativo|2|singular
es-UY-montevideo|verb_infinitive|poder|poder
es-UY-montevideo|adjective|clara|claro|feminine|singular
```

Do not treat these as duplicates:

```text
ir
yo voy
vos vas
```

Do not treat these as duplicates:

```text
claro masculine singular
clara feminine singular
```

They may share lemma, but they are different training units.

---

## 10. Pydantic schemas

## 10.1 ReplyBundle

```python
from pydantic import BaseModel, Field
from typing import Literal

class ReplyContext(BaseModel):
    target_locale: str = "es-UY-montevideo"
    channel: Literal["whatsapp_text", "whatsapp_voice", "in_person", "support_chat", "email"]
    situation: str | None = None
    tone: Literal["neutral", "polite_neutral", "friendly", "firm_not_rude", "simple_a1_a2"]
    user_level: Literal["A1", "A2", "B1", "B2"] = "A2"

class ReplyBundle(BaseModel):
    target_locale: str
    dialect_stamp: str
    source_language: str
    intent_summary_ru: str
    intent_summary_en: str | None = None
    recommended_reply: str
    simple_reply: str | None = None
    short_reply: str | None = None
    more_formal_reply: str | None = None
    notes_ru: list[str] = Field(default_factory=list)
    notes_en: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    can_add_to_training: bool = True
```

## 10.2 TrainingCandidate

```python
class TrainingCandidate(BaseModel):
    candidate_id: str
    item_type: Literal["noun", "adjective", "verb_form", "verb_infinitive"]
    surface_text: str
    display_text: str
    lemma: str | None = None
    locale_variant: str = "es-UY-montevideo"
    translations_ru: list[str]
    translations_en: list[str]
    context_translation_ru: str | None = None
    context_translation_en: str | None = None
    grammar: dict = Field(default_factory=dict)
    governance: list[str] = Field(default_factory=list)
    example_es: str | None = None
    example_ru: str | None = None
    example_en: str | None = None
    status_hint: Literal["new", "learning", "known", "ignored", "duplicate_possible"] = "new"
    canonical_key: str | None = None
```

## 10.3 ExtractionBundle

```python
class ExtractionBundle(BaseModel):
    target_locale: str = "es-UY-montevideo"
    source_language: str
    spanish_text: str
    candidates: list[TrainingCandidate]
    skipped_reasoning_summary: list[str] = Field(default_factory=list)
```

---

## 11. Prompt contracts

Store prompts in `apps/api/src/decime_api/prompts/`.

## 11.1 `translate_to_esuy.md`

Purpose: Faithful RU/EN → es-UY translation (what the user will say/send). No reply invention.

Prompt requirements:

```text
You are Decime UY, a communication copilot for Uruguayan Spanish in Montevideo.
Translate source_text into natural, locally usable Spanish for the requested channel and tone.
Do not invent replies to another message.
Do not produce Spain-specific or Mexican/Colombian-flavored output unless explicitly requested.
Avoid excessive Buenos Aires slang.
Use low-slang, polite-neutral Montevideo Spanish by default.
Prefer simple A1/A2-friendly structures if user_level is A1 or A2.
Return only JSON matching the schema.
```

Must include in prompt variables:

```text
source_language
source_text
context.channel
context.situation
context.tone
context.user_level
context.target_locale
```

## 11.2 `extract_training_items.md`

Purpose: Extract atomic training items only.

Prompt requirements:

```text
Extract MVP training candidates from the Spanish text.
Extract only these item types: noun, adjective, verb_form, verb_infinitive.
Do not extract full expressions, idioms, sentence patterns, or complete replies in MVP.

Rules:
- For nouns, include article, gender, number, lemma, RU/EN translations.
- For adjectives, include gender, number and common forms if relevant.
- For verbs, extract the exact observed surface form as a separate item.
- A verb form is not the same as its infinitive.
- Include display_text with pronoun when useful: "vos podés", "yo voy".
- Include lemma, person, number, tense, mood, voseo flag if relevant.
- Include governance/preposition patterns when known: "pagar con", "depender de", "poder + infinitivo".
- Include exact and contextual translations in Russian and English.
- Use the source Spanish sentence as example_es.
- Avoid private data, names, addresses, phone numbers.
- Avoid low-value function words unless crucial for a verb form or noun/adjective card.
- Return only JSON matching the schema.
```

## 11.3 `locale_validate_uy.md`

Purpose: Detect obvious non-Uruguayan output.

Prompt requirements:

```text
Review the Spanish output for Uruguay/Montevideo suitability.
Flag Spain-specific, Mexican-specific, overly formal textbook, or excessive Buenos Aires slang.
Do not rewrite unless there is a clear issue.
Return JSON with status: ok / warning / rewrite_needed.
```

This can be added after the first compose flow works.

---

## 12. Core backend workflows

## 12.1 Text translate workflow

```python
async def translate_to_esuy(request: TranslateToEsRequest) -> ReplyBundle:
    # 1. Save request
    # 2. Call LLM provider with structured output
    # 3. Validate Pydantic ReplyBundle
    # 4. Save output
    # 5. Return bundle
```

## 12.2 Audio transcription workflow

```python
async def transcribe_audio(file, source_type, language_hint):
    # 1. Save uploaded file to storage
    # 2. Call STT provider
    # 3. Save transcript
    # 4. Return transcript object
```

## 12.3 Audio synthesis workflow

```python
async def synthesize_audio(text, locale, mode, speed):
    # 1. Hash text + locale + voice + speed + model
    # 2. Check cache in audio_files
    # 3. If exists, return cached URL
    # 4. Call TTS provider
    # 5. Save file to storage
    # 6. Save audio_files row
    # 7. Return URL
```

## 12.4 Add to training workflow

```python
async def extract_training_candidates(spanish_text, source_context):
    # 1. Call LLM extractor with strict schema
    # 2. Build canonical keys
    # 3. Compare with existing user items
    # 4. Mark status_hint
    # 5. Save extraction_run
    # 6. Return candidates for approval
```

## 12.5 Candidate approval workflow

```python
async def approve_candidates(extraction_id, approved_candidate_ids, list_id):
    # 1. Load extraction candidates
    # 2. Filter approved
    # 3. Skip duplicates unless user chooses otherwise
    # 4. Insert training_items
    # 5. Queue/generate audio for each display_text
    # 6. Return created items
```

## 12.6 Review scheduling workflow

Simple MVP scheduling:

```python
REVIEW_STAGES = [
    0,                 # new: now
    10 * MINUTE,
    1 * DAY,
    3 * DAY,
    7 * DAY,
    14 * DAY,
    30 * DAY,
]
```

Grade behavior:

```text
Again → stage max(current - 1, 0), next_review_at = now + 10 min
Hard  → stage unchanged or +1 slowly
Good  → stage +1
Easy  → stage +2
```

---

## 13. Frontend pages and components

## 13.1 Pages

```text
/
  landing / entry screen

/app
  main dashboard

/app/compose
  smart translator / reply composer

/app/audio
  audio input and transcription

/app/history
  previous requests and replies

/app/training
  training lists and due reviews

/app/training/lists/[id]
  list detail

/app/training/review
  review session

/app/settings
  user level, languages, target locale, provider settings
```

## 13.2 Main components

```text
ComposeInput
ContextSelector
ReplyBundleCard
DialectStamp
AudioRecorder
AudioPlayer
CopyForWhatsAppButton
AddToTrainingButton
TrainingCandidateReview
TrainingListSelector
TrainingItemCard
ReviewCard
ReviewGradeButtons
HistoryItem
```

## 13.3 Mobile-first UI priorities

The app must be usable from a phone while switching to WhatsApp.

Important buttons:

- Copy answer
- Play audio
- Add to training
- Make shorter
- More polite
- Simpler A1/A2
- Explain grammar

Do not overload the first screen.

---

## 14. UI copy examples

### Main compose screen

```text
What do you need to say or understand?
[Text box]

Context:
[WhatsApp] [In person] [Support] [Doctor] [Shop]

Tone:
[Neutral] [Polite] [Friendly] [Firm but not rude] [Simple]

[Generate]
```

### Reply card

```text
🇺🇾 Uruguay · Montevideo · WhatsApp · neutral amable · A2-friendly

Recommended:
Hola, quería consultar si se puede pagar con tarjeta.

Simpler:
Hola, ¿se puede pagar con tarjeta?

More formal:
Hola, quisiera consultar si es posible pagar con tarjeta.

[Copy] [Play audio] [Add to training]
```

### Add to training candidate review

```text
Add to training

Choose list:
[WhatsApp / real messages ▼]

Candidates:
✓ vos podés — ты можешь / можешь — present, voseo
✓ la factura — счёт / квитанция — feminine
✓ mandar — отправлять / присылать — mandar algo a alguien

[Add selected]
```

---

## 15. Testing strategy

## 15.1 Backend unit tests

Required tests:

- Pydantic schema validation for `ReplyBundle`.
- Pydantic schema validation for `ExtractionBundle`.
- canonical key generation.
- deduplication behavior.
- SRS scheduling behavior.
- audio cache hash generation.

## 15.2 Golden tests for prompts

Create test cases in YAML:

```yaml
- id: mercado_libre_return_001
  input_ru: "Я хочу уточнить, нужно ли мне самому отправлять товар или ждать курьера."
  expected_contains:
    - "quería"
    - "confirmar"
    - "mandar"
  forbidden_contains:
    - "vosotros"
    - "vale"
```

For extraction:

```yaml
- id: extraction_001
  spanish_text: "¿Me podés mandar la factura?"
  expected_items:
    - item_type: verb_form
      display_text: "vos podés"
      lemma: "poder"
    - item_type: verb_infinitive
      surface_text: "mandar"
    - item_type: noun
      surface_text: "la factura"
      gender: "feminine"
```

## 15.3 Manual QA checklist

For every generated reply:

- Does it sound natural in Uruguay?
- Is it not too Spain-like?
- Is it not too Buenos Aires slangy?
- Is it A1/A2-friendly when requested?
- Is the translation faithful to user intent?
- Is tone appropriate?
- Would I send this in WhatsApp?

For extracted candidates:

- Is noun article correct?
- Is gender correct?
- Is verb form exact and not replaced by infinitive?
- Is pronoun correct?
- Is tense/mood plausible?
- Are translations accurate and contextual?
- Is this item worth learning?

---

## 16. Cursor workflow

Do not ask Cursor to build everything at once. Use small tasks.

## 16.1 Initial Cursor setup prompt

```text
You are helping build Decime UY, a Next.js + FastAPI + Supabase MVP.
Read docs/product_brief.md and docs/development_brief.md first.
Do not implement features outside MVP scope.
Prioritize typed schemas, testable backend services, and mobile-first simple UI.
Before changing code, summarize the files you will touch.
After changes, provide validation commands.
```

## 16.2 Task 1 — repo skeleton

```text
Create the monorepo skeleton described in docs/development_brief.md.
Add apps/api FastAPI app with /health endpoint.
Add apps/web Next.js app with a simple home page.
Do not add AI logic yet.
Add .env.example.
Add README with local dev commands.
```

Acceptance:

```bash
cd apps/api && uvicorn decime_api.main:app --reload
curl http://localhost:8000/health
cd apps/web && pnpm dev
```

## 16.3 Task 2 — schemas

```text
Implement Pydantic schemas for compose, audio and training according to docs/development_brief.md.
Add unit tests for schema validation.
No database yet.
```

## 16.4 Task 3 — translate endpoint with fake provider

```text
Implement POST /api/v1/translate/text using a FakeLLMProvider that returns deterministic ReplyBundle data.
Add tests.
Connect frontend Quick Reply / Live forms to this endpoint.
```

## 16.5 Task 4 — OpenAI provider

```text
Add OpenAILLMProvider for translate_to_esuy with structured output.
Keep FakeLLMProvider as test provider.
Use env var OPENAI_TEXT_MODEL.
Log latency and model name.
```

## 16.6 Task 5 — Supabase schema

```text
Add Supabase migration for locale_variants, situations, reply_requests, reply_outputs, audio_files, transcripts, training_lists, training_items, extraction_runs, training_attempts, event_log.
Add seed for es-UY-montevideo and starter situations.
```

## 16.7 Task 6 — audio upload/transcription

```text
Implement /api/v1/audio/transcribe.
Use OpenAISpeechProvider with gpt-4o-mini-transcribe.
Save uploaded audio metadata and transcript.
Add frontend audio upload/record UI.
```

## 16.8 Task 7 — TTS

```text
Implement /api/v1/audio/synthesize.
Use gpt-4o-mini-tts.
Add audio caching by text+locale+model+voice+mode hash.
Add Play audio button to ReplyBundleCard.
```

## 16.9 Task 8 — extraction with fake provider

```text
Implement /api/v1/training/extract-candidates using FakeTrainingExtractor first.
Return noun/adjective/verb_form/verb_infinitive candidates.
Build TrainingCandidateReview UI.
```

## 16.10 Task 9 — OpenAI extraction

```text
Implement OpenAITrainingExtractor with strict structured output.
Use docs prompt contract.
Add golden tests with mocked provider outputs.
```

## 16.11 Task 10 — approve/save training items

```text
Implement /api/v1/training/approve-candidates.
Generate canonical keys.
Deduplicate per user.
Save approved items to training_items.
Add TrainingListSelector.
```

## 16.12 Task 11 — review mode

```text
Implement due queue and review submit endpoint.
Add RU/EN→ES, ES→RU/EN and audio→meaning cards.
Implement Again/Hard/Good/Easy scheduling.
```

---

## 17. Development milestones and time estimates

### Phase 0 — Skeleton and docs

Estimate: 8–16 hours

Deliverables:

- repo structure;
- FastAPI health endpoint;
- Next.js home page;
- env setup;
- docs in repo.

### Phase 1 — Text reply composer

Estimate: 30–60 hours

Deliverables:

- compose form;
- context selector;
- structured LLM output;
- reply card;
- history save.

### Phase 2 — Audio

Estimate: 30–70 hours

Deliverables:

- audio upload/record;
- STT;
- TTS;
- audio cache;
- audio playback.

### Phase 3 — Add to training

Estimate: 40–90 hours

Deliverables:

- candidate extraction;
- approval UI;
- save items;
- canonical keys;
- base lists.

### Phase 4 — Review mode

Estimate: 30–70 hours

Deliverables:

- list view;
- due review queue;
- SRS;
- audio review.

### Phase 5 — WhatsApp convenience

Estimate: 10–25 hours for copy/upload + Android Share (done).

Deliverables:

- copy-to-WhatsApp;
- WhatsApp audio upload / Share flow;
- no Twilio webhook ([out_of_scope.md](out_of_scope.md)).

### Overall MVP estimate

Personal MVP:

```text
120–250 hours
```

Demo-quality MVP:

```text
220–400 hours
```

---

## 18. Twilio WhatsApp Sandbox

**Removed from plans.** Use Capacitor Share and clipboard instead. See [out_of_scope.md](out_of_scope.md).

---

## 19. Security and privacy requirements

Even for MVP:

- never commit API keys;
- store audio files under user-specific paths;
- allow deletion of audio/transcripts later;
- do not expose service role key to frontend;
- use Supabase Row Level Security before external users;
- avoid storing unnecessary personal WhatsApp content;
- mask phone numbers/addresses in logs where possible;
- add privacy note before uploading audio.

Minimum UI note:

```text
Audio and text you upload will be processed to generate translation, replies and training items. Do not upload sensitive information during MVP testing.
```

---

## 20. Quality control for Uruguay Spanish

## 20.1 Seed test cases

Create test cases for:

- Mercado Libre return;
- asking if card payment is accepted;
- asking for address/time;
- doctor appointment;
- delivery coordination;
- rent/apartment visit;
- neighbor small talk.

## 20.2 Forbidden pattern list

Initial forbidden or warning terms:

```text
vosotros
vale
móvil
ordenador
coger
```

These are not always “wrong” globally, but should trigger warnings for Uruguay-focused output.

## 20.3 Native review

Before showing to other users, have 1–2 Uruguay/Montevideo native speakers review:

- base lists;
- 20 common generated replies;
- audio naturalness;
- tone labels.

---

## 21. Base seed data

Seed situations:

```text
shop_payment
mercado_libre_return
delivery_coordination
doctor_appointment
pharmacy
bank_or_service
rent_apartment
neighbor_chat
internet_problem
ask_for_repetition
```

Seed channels:

```text
whatsapp_text
whatsapp_voice
in_person
support_chat
email
```

Seed tones:

```text
neutral
polite_neutral
friendly
firm_not_rude
simple_a1_a2
```

---

## 22. Minimum validation commands

Backend:

```bash
cd apps/api
python -m pytest
python -m ruff check .
python -m uvicorn decime_api.main:app --reload
```

Frontend:

```bash
cd apps/web
pnpm lint
pnpm test
pnpm dev
```

End-to-end manual validation:

```text
1. Open /app/compose
2. Enter Russian phrase
3. Generate Spanish reply
4. Play audio
5. Add to training
6. Approve candidates
7. Open review
8. Review approved item
```

---

## 23. Known implementation risks

### Risk 1 — extraction hallucination

Mitigation:

- strict schemas;
- user approval screen;
- golden tests;
- save raw output for inspection.

### Risk 2 — wrong grammar metadata

Mitigation:

- show grammar as editable later;
- use native/user correction loop;
- initially focus on high-confidence items only.

### Risk 3 — poor Uruguayan dialect consistency

Mitigation:

- locale prompt;
- locale validator;
- forbidden pattern list;
- manual QA.

### Risk 4 — audio too unnatural

Mitigation:

- support voice/model switching (OpenAI / Orpheus);
- cache approved audio.

### Risk 5 — product becomes too broad

Mitigation:

- keep MVP to Montevideo;
- no full expressions yet;
- no full course;
- no production WhatsApp until PWA works.

---

## 24. External source notes

Use current official docs before implementation details are finalized:

- OpenAI Responses / migration: https://platform.openai.com/docs/guides/responses-vs-chat-completions
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- OpenAI Speech to Text: https://platform.openai.com/docs/guides/speech-to-text
- OpenAI Text to Speech: https://platform.openai.com/docs/guides/text-to-speech
- Supabase Docs: https://supabase.com/docs
- Next.js Docs: https://nextjs.org/docs/app/getting-started
- FastAPI Docs: https://fastapi.tiangolo.com/

---

## 25. Cursor instruction to keep in repository

Put this in `docs/cursor_working_rules.md` or `.cursor/rules`:

```text
Project: Decime UY.

Read docs/product_brief.md and docs/development_brief.md before coding.
Build only MVP features unless explicitly asked.
Prefer small, testable changes.
Use typed schemas and structured LLM outputs.
Keep providers replaceable.
Do not hardcode OpenAI directly into business logic.
Do not auto-add training items without user approval.
For learning items, surface_text is the primary memorized form; lemma is metadata.
Keep Uruguay/Montevideo as the only active target locale in MVP.
Avoid full expression extraction in MVP.
After each coding step, provide validation commands and expected results.
```
