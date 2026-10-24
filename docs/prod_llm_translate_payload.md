# Prod LLM payload: translate_to_esuy

**Last updated:** 2026-10-17  
**Purpose:** Exact shape of what production sends to the text LLM for RU/EN → es-UY translation (not the raw HTTP body alone — system + human + JSON Schema).

Source of truth for assembly: [`apps/api/src/decime_api/services/ai/openai_llm.py`](../apps/api/src/decime_api/services/ai/openai_llm.py) (`_translate_user_content`, `_translate_once`).

---

## Flow

UI → `POST /api/v1/translate/text` → `OpenAILLMProvider.translate_to_esuy` → LangChain `ainvoke_structured` (`ChatPromptTemplate` system+human + `with_structured_output` / `json_schema` strict).

```text
QR / Live  →  TranslateToEsRequest  →  _translate_user_content
                                              ↓
translate_to_esuy.md (system)  ──→  ainvoke_structured  ←── reply_bundle_json_schema
                                              ↓
                                         ChatOpenAI
```

Related: [prompt_contracts.md](prompt_contracts.md), runtime prompt [`translate_to_esuy.md`](../apps/api/src/decime_api/prompts/translate_to_esuy.md), schema [`compose.py`](../apps/api/src/decime_api/schemas/compose.py).

---

## 1. What the frontend sends (HTTP)

Endpoint: `/api/v1/translate/text` ([`translateToEsuy`](../apps/web/src/lib/api.ts)).  
Body schema: `TranslateToEsRequest` — **no** `output_options`, **no** `tone` / `situation`.

### Quick Reply

From [`QuickReplyForm`](../apps/web/src/app/app/quick-reply/QuickReplyForm.tsx). Chips map to `user_level`:

- Recommended → `user_level: null` (any complexity)
- Simple (A2) → `user_level: "A2"`

```json
{
  "source_language": "ru",
  "source_text": "Можно перенести встречу на пятницу?",
  "context": {
    "target_locale": "es-UY-montevideo",
    "channel": "whatsapp_text",
    "user_level": null
  }
}
```

### Live Chat

From [`LiveChatForm`](../apps/web/src/app/app/live/LiveChatForm.tsx) — channel only; level/register fixed in the system prompt for `in_person`:

```json
{
  "source_language": "ru",
  "source_text": "Где ближайшая аптека?",
  "context": {
    "target_locale": "es-UY-montevideo",
    "channel": "in_person"
  }
}
```

---

## 2. What actually goes to the LLM

| Role | Content |
|------|---------|
| `system` | Full text of [`prompts/translate_to_esuy.md`](../apps/api/src/decime_api/prompts/translate_to_esuy.md) |
| `human` | Short instructions + JSON payload (below) |
| response | Structured Outputs: schema `reply_bundle` ([`reply_bundle_json_schema`](../apps/api/src/decime_api/services/ai/llm_json_schemas.py)), `strict=True` |

Human assembly: `_translate_user_content`. Context is `model_dump(exclude_none=True)` so Live omits null `user_level`.

```json
{
  "source_language": "...",
  "source_text": "...",
  "context": {
    "target_locale": "es-UY-montevideo",
    "channel": "whatsapp_text"
  }
}
```

With Simple chip, `"user_level": "A2"` is included in `context`.

Human text also instructs: single translation in `recommended_reply`; A2 → short simple wording; otherwise natural any-level. On contamination retry, prefix `CRITICAL RETRY: ...`.

---

## 3. Expected model output (ReplyBundle)

Required fields:

- `target_locale`, `dialect_stamp`, `source_language`
- `intent_summary_ru`, `intent_summary_en`
- `recommended_reply`
- `warnings`, `can_add_to_training`

No variant fields (`simple_reply` / …) and no `notes_*`.

If `dialect_stamp` is empty after parse, the server fills it via [`build_dialect_stamp(context)`](../apps/api/src/decime_api/services/compose/dialect_stamp.py) (`channel` + `A2` or `any`).

---

## 4. Debugging notes

- Production translate = **faithful translation** of what the user will say/send.
- Removed from this path: `tone`, `situation`, entire `output_options` (including former defaults like `include_training_preview` that only appeared after `model_dump`).
- This document covers **only** `translate_to_esuy` — not `understand_incoming`.
