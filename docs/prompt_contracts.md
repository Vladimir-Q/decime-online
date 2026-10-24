# Decime UY — Prompt Contracts

**Version:** 0.2  
**Last updated:** 2026-06-23  
**Location:** `apps/api/src/decime_api/prompts/`

Human instructions for the four live operations are in the LangSmith chat templates described in [langsmith_prompt_management.md](langsmith_prompt_management.md). The default process still loads the local copies (`DECIME_PROMPT_SOURCE=local`). `locale_validate_uy.md` is not loaded.

---

## understand_incoming.md

**Purpose:** Translate incoming Spanish to RU or EN for Quick Reply (one faithful translation).

**Prompt variables:**

```text
source_text
source_language
target_language
locale_variant
channel
```

**Output schema:** structured JSON — translation, optional dialect/stt notes (see `llm_json_schemas.py`).

**Rules:** Do not invent context; preserve meaning; note Uruguay-specific forms when helpful.

---

## translate_to_esuy.md

**Purpose:** Faithful RU/EN → es-UY translation only (what the user will say/send). Does **not** invent replies to another message.

**System requirements:** see `apps/api/src/decime_api/prompts/translate_to_esuy.md`.

**Prod wire format (HTTP vs system/human/schema examples):** [prod_llm_translate_payload.md](prod_llm_translate_payload.md).

**Semantic fidelity (critical):** Do not add/remove thanks, follow-up questions, offers, or assumptions. Optional `context.user_level` (`A2` vs absent/null) changes **complexity**, not **meaning**. Channel sets register (WhatsApp vs in-person).

**Single output:** only `recommended_reply` (no variant fields / notes).

**Prompt variables:**

```text
source_language
source_text
context.channel
context.user_level   # optional; null/absent = any; A2 = simple
context.target_locale
```

**Output schema:** slim `ReplyBundle` — see [prod_llm_translate_payload.md](prod_llm_translate_payload.md)

---

## extract_training_items.md

**Purpose:** Extract atomic training items only.

**System requirements:**

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

**Output schema:** `ExtractionBundle` (see `docs/development_brief.md` §10.3)

---

## locale_validate_uy.md

**Purpose:** Detect obvious non-Uruguayan output. Add after compose flow works.

**System requirements:**

```text
Review the Spanish output for Uruguay/Montevideo suitability.
Flag Spain-specific, Mexican-specific, overly formal textbook, or excessive Buenos Aires slang.
Do not rewrite unless there is a clear issue.
Return JSON with status: ok / warning / rewrite_needed.
```
