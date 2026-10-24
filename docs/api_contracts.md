# Decime UY — API Contracts

**Version:** 0.2  
**Last updated:** 2026-06-23  
**Base prefix:** `/api/v1`

See `docs/development_brief.md` §7 for full context. Endpoints below are the MVP contract.

---

## Auth (VM / self-hosted)

See [docs/vm_auth.md](vm_auth.md). When `AUTH_ENABLED=true`, protected routes require `Authorization: Bearer <jwt>`.

| Method | Path | Access |
|--------|------|--------|
| GET | `/api/v1/auth/config` | public |
| POST | `/api/v1/auth/login` | public |
| POST | `/api/v1/auth/register` | public if registration enabled |
| GET | `/api/v1/auth/me` | user |
| GET/POST/PATCH | `/api/v1/auth/users` | admin |

---

## Health (Phase 0)

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "app": "Decime UY",
  "env": "local",
  "auth_enabled": "false",
  "llm_provider": "openai",
  "llm_orchestrator": "langchain",
  "llm_model": "gpt-6-luna",
  "stt_provider": "faster_whisper",
  "stt_model": "whisper-base",
  "tts_provider": "orpheus",
  "tts_model": "orpheus/javi"
}
```

Fields vary with `.env`. Text LLM is OpenAI / OpenAI-compatible via LangChain only.

---

## Understand incoming text (Quick Reply)

```http
POST /api/v1/incoming/understand-text
```

Request:

```json
{
  "source_text": "¿Me podés mandar la factura?",
  "source_language": "es",
  "target_language": "ru",
  "locale_variant": "es-UY-montevideo",
  "channel": "whatsapp_text"
}
```

Response: single translation + optional notes (see `schemas/incoming.py`). Used by Quick Reply **Translate** step.

---

## Translate to es-UY

```http
POST /api/v1/translate/text
```

Faithful translation of the user's draft (RU/EN/auto) into Uruguayan Spanish. Not reply composition.

Request:

```json
{
  "source_language": "auto",
  "source_text": "Я хочу уточнить, можно ли оплатить картой.",
  "context": {
    "target_locale": "es-UY-montevideo",
    "channel": "whatsapp_text",
    "user_level": null
  }
}
```

`channel`: `whatsapp_text` | `in_person`.  
`user_level`: omit/`null` = any (Recommended); `"A2"` = Simple. Live omits `user_level`.

Response:

```json
{
  "request_id": "uuid",
  "target_locale": "es-UY-montevideo",
  "dialect_stamp": "🇺🇾 Uruguay · Montevideo · WhatsApp · any-friendly",
  "source_language": "ru",
  "intent_summary_ru": "Пользователь хочет вежливо уточнить, можно ли оплатить картой.",
  "intent_summary_en": "The user wants to politely ask if card payment is accepted.",
  "recommended_reply": "Hola, quería consultar si se puede pagar con tarjeta.",
  "warnings": [],
  "can_add_to_training": true
}
```

---

## Transcribe audio

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

---

## Synthesize audio

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

---

## Extract training candidates

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
  "candidates": []
}
```

See `docs/development_brief.md` §7.4 for full candidate schema.

---

## Approve candidates

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
  "created_items": [],
  "skipped_duplicates": []
}
```

---

## Training review

```http
GET /api/v1/training/review/next?list_id=uuid&limit=20
POST /api/v1/training/review/submit
```

See `docs/development_brief.md` §7.6 for request/response shapes.
