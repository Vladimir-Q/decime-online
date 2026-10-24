# Decime UY — Technical Document for Cursor: Qwen3 4B + Uruguay Locale Pack

**Purpose:** configure Decime UY to use Qwen3 4B locally for text tasks and implement a controlled Uruguay / Montevideo Spanish style layer.

**Target milestone:** private VM alpha.

**Audience:** Cursor / AI coding agent.

**Language scope:** Russian/English user input → Uruguayan Spanish output; Spanish input → Russian/English translation; training card extraction from Spanish text.

---

## 1. Strategic decision

Use Qwen3 4B as the default local LLM for text work, but do not rely on the raw model to “know Uruguayan Spanish” perfectly.

The correct architecture is:

```text
Qwen3 4B
+ Uruguay locale pack
+ strict prompts
+ glossary
+ forbidden terms
+ JSON schemas
+ post-validation
+ LocaleCriticUY
+ eval cases
```

Do not implement fine-tuning in this milestone.

The goal is to make Qwen3 4B usable through **controlled generation**, not by changing model weights.

---

## 2. Model choice

### Default model

```text
qwen3:4b
```

### Runtime

```text
Ollama
```

### Intended usage

```text
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
```

### Why Qwen3 4B

Qwen3 4B is light enough for CPU-only private VM testing and supports multilingual instruction-following and translation. It has 4.0B parameters and a native 32,768-token context window according to the Qwen model card.

Ollama provides `qwen3:4b` as a Q4_K_M quantized model, around 2.5 GB, which is appropriate for the current VM alpha.

---

## 3. Runtime constraints

Target VM:

```text
e2-highmem-4
4 vCPU
32 GB RAM
CPU-only
```

Implication:

```text
Qwen3 4B should be usable.
Qwen3 8B may be tested later as quality mode.
Do not run large models by default.
Do not use thinking mode for normal requests.
Keep prompts compact.
Keep conversation context trimmed.
Use low-latency request paths.
```

---

## 4. Ollama configuration

### Pull model

```bash
ollama pull qwen3:4b
```

### Health check

```bash
curl http://localhost:11434/api/chat \
  -d '{
    "model": "qwen3:4b",
    "messages": [
      {"role": "user", "content": "Respond with OK only. /no_think"}
    ],
    "stream": false,
    "think": false
  }'
```

### Environment variables

Add or confirm:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3:4b
OLLAMA_KEEP_ALIVE=30m

LLM_TEMPERATURE_TRANSLATION=0.2
LLM_TEMPERATURE_EXTRACTION=0.0
LLM_TOP_P=0.8
LLM_MAX_OUTPUT_TOKENS=1200
LLM_THINK=false
```

### Ollama request defaults

For all Decime production requests:

```json
{
  "model": "qwen3:4b",
  "stream": false,
  "think": false,
  "options": {
    "temperature": 0.2,
    "top_p": 0.8,
    "num_predict": 1200
  }
}
```

For extraction:

```json
{
  "model": "qwen3:4b",
  "stream": false,
  "think": false,
  "options": {
    "temperature": 0,
    "top_p": 0.8,
    "num_predict": 1600
  }
}
```

Use JSON schema through Ollama `format` where possible.

---

## 5. Required files to add

Create:

```text
apps/api/src/decime_api/locale_packs/es_uy_montevideo/
  style_guide.md
  glossary.yaml
  forbidden_terms.yaml
  few_shots_assistant.yaml
  few_shots_live.yaml
  few_shots_extraction.yaml
  locale_critic_rules.yaml
  eval_cases.yaml
```

Create code modules:

```text
apps/api/src/decime_api/locale/
  __init__.py
  locale_pack_loader.py
  es_uy_rules.py
  locale_critic_uy.py
```

Update prompts:

```text
apps/api/src/decime_api/prompts/
  assistant_reply.md
  incoming_translation.md
  live_translate.md
  extract_training_items.md
```

Add tests:

```text
apps/api/tests/test_locale_pack_es_uy.py
apps/api/tests/test_locale_critic_uy.py
apps/api/tests/test_qwen_prompt_contracts.py
apps/api/tests/test_training_extraction_es_uy.py
```

---

# 6. Uruguay / Montevideo style guide

Implement this content in:

```text
locale_packs/es_uy_montevideo/style_guide.md
```

## 6.1 Locale identity

```yaml
locale_id: es-UY-montevideo
country: Uruguay
region: Montevideo
product_label: Uruguay / Montevideo Spanish
output_goal: natural, concise, locally usable Spanish for Uruguay
avoid_goal: generic textbook Spanish or country-mixed Latin American Spanish
```

## 6.2 Global style

Output must be:

```text
natural
clear
brief
polite by default
not over-slangy
not Spain-specific
not Mexicanized
not Colombianized
not excessively Buenos Aires porteño
```

Decime is not trying to sound like a teenager from Montevideo. It should produce safe, practical, locally acceptable Spanish.

## 6.3 Default register

Default register for Assistant:

```text
Formal first
Friendly second
Simple third
```

Default register for Live:

```text
polite
brief
sufficiently formal
single output only
```

## 6.4 Formal variant

Formal should be polite and short, but not bureaucratic.

Prefer:

```text
Hola, quería consultar...
Hola, quería confirmar...
Quisiera consultar...
Quisiera confirmar...
¿Sería posible...?
¿Se puede...?
¿Me podría indicar...?
¿Me podría confirmar...?
```

For formal output, avoid too much direct `vos`.

Acceptable strategies:

```text
impersonal: ¿Se puede pagar con tarjeta?
conditional: ¿Sería posible...?
polite first person: Quería consultar...
usted-style when needed: ¿Podría confirmarme...?
```

Examples:

```text
RU: Можно оплатить картой?
ES formal: Disculpe, ¿se puede pagar con tarjeta?

RU: Я хотел уточнить, нужно ли мне самому отправить товар.
ES formal: Hola, quería confirmar si tengo que enviar el producto por mi cuenta.
```

## 6.5 Friendly variant

Friendly should be natural for WhatsApp and light everyday communication.

Prefer:

```text
Dale
Perfecto
Gracias
Te hago una consulta
Quería consultarte
¿Me podés...?
¿Te sirve si...?
Avisame, por favor
```

Use voseo naturally where appropriate:

```text
vos podés
vos querés
vos tenés
avisame
mandame
decime
pasame
confirmame
```

Examples:

```text
RU: Можешь отправить мне счёт?
ES friendly: ¿Me podés mandar la factura?

RU: Да, могу подойти завтра около 10:30.
ES friendly: Dale, puedo pasar mañana tipo 10:30, si te sirve.
```

## 6.6 Simple variant

Simple is for A1/A2-friendly output.

Rules:

```text
short sentences
common words
avoid complex subordinate clauses
avoid unnecessary idioms
preserve meaning over elegance
```

Examples:

```text
RU: Я хотел уточнить, могу ли я оплатить картой.
ES simple: ¿Puedo pagar con tarjeta?

RU: Можешь отправить мне счёт завтра?
ES simple: ¿Me podés mandar la factura mañana?
```

## 6.7 Live output

Live output should be:

```text
one option only
quick
polite
brief
clear
```

Examples:

```text
RU: Скажите, пожалуйста, можно оплатить картой?
ES live: Disculpe, ¿se puede pagar con tarjeta?

RU: Я не очень хорошо говорю по-испански.
ES live: Disculpe, no hablo muy bien español.

RU: Можно повторить, пожалуйста?
ES live: ¿Me puede repetir, por favor?
```

## 6.8 Voseo rules

Uruguay uses voseo widely. In Montevideo, formal contexts may use verbal voseo with `tú`, but Decime should avoid producing confusing mixed forms unless specifically needed.

Practical product rules:

```text
Friendly:
  use vos + voseo forms naturally:
  vos podés, vos querés, vos tenés, vos sabés

Formal:
  prefer impersonal / conditional / usted-style:
  ¿Se puede...?
  ¿Sería posible...?
  ¿Podría...?
  Quería consultar...

Simple:
  use common short forms; voseo is allowed:
  ¿Me podés...?
  ¿Tenés...?
```

Avoid:

```text
vosotros
vosotras
podéis
tenéis
sois
```

Avoid incorrect or vulgar forms:

```text
cantastes
comistes
vivistes
habés
sós
vai
```

## 6.9 Subjunctive

For Uruguay, prefer tuteo subjunctive forms where relevant:

```text
cuando puedas
si querés que lo haga
cuando tengas tiempo
```

Avoid overusing:

```text
cuando podás
cuando tengás
```

## 6.10 Imperatives

Use Rioplatense/Uruguayan forms in friendly contexts:

```text
decime
mandame
avisame
pasame
esperame
confirmame
explicame
ayudame
```

Formal/live should often avoid direct imperative:

```text
¿Me podría mandar...?
¿Me puede avisar...?
```

## 6.11 Numbers

Numbers must preserve input format.

Rules:

```text
10:30 → 10:30
diez y media → diez y media
1000 → 1000
mil → mil
28.395 → 28.395
veintiocho mil trescientos noventa y cinco → veintiocho mil trescientos noventa y cinco
```

Do not convert digits into words or words into digits unless explicitly requested.

## 6.12 Mixed input terms

If the user inserts a Spanish word into Russian/English input, preserve it if semantically appropriate.

Example:

```text
RU input: Скажи, что я уже оплатил la factura.
ES: Ya pagué la factura.
```

Do not translate `la factura` into a different noun unless context requires it.

---

# 7. Glossary

Implement starter glossary in:

```text
locale_packs/es_uy_montevideo/glossary.yaml
```

```yaml
locale_id: es-UY-montevideo

preferred_terms:
  card:
    es: tarjeta
    ru: карта
    en: card

  bill_invoice:
    es_options:
      - la factura
      - el recibo
      - la boleta
    guidance: >
      Use "la factura" for bill/invoice in service/payment contexts.
      Use "el recibo" for receipt/proof of payment.
      Use "la boleta" only when context supports it.

  courier:
    es_options:
      - el cadete
      - el repartidor
    guidance: >
      Use "cadete" for local pickup/delivery person when natural in Uruguay.
      Use "repartidor" for generic delivery person.

  bus:
    es_options:
      - el ómnibus
      - el bus
    guidance: >
      "Ómnibus" is locally appropriate in Uruguay.
      "Bus" is also understandable and may be simpler.

  id_card:
    es: la cédula
    ru: удостоверение личности / cédula
    en: ID card

  pharmacy:
    es: la farmacia

  health_provider:
    es: la mutualista
    guidance: Use in Uruguay healthcare context when appropriate.

  rent:
    es: el alquiler

  landlord:
    es_options:
      - el dueño
      - la dueña
      - el propietario
      - la propietaria
    guidance: >
      "Dueño/dueña" is natural in everyday speech.
      "Propietario/propietaria" is more formal.

  appointment:
    es_options:
      - la cita
      - el turno
    guidance: >
      "Turno" is common for appointments in healthcare/service contexts.
```

Add ability to load this glossary into prompts.

---

# 8. Forbidden terms

Implement:

```text
locale_packs/es_uy_montevideo/forbidden_terms.yaml
```

```yaml
hard_forbidden:
  - vosotros
  - vosotras
  - podéis
  - tenéis
  - sois
  - estáis
  - habéis

spain_specific_warn:
  - vale
  - ordenador
  - móvil
  - piso
  - coger

mexico_or_other_latam_warn:
  - celular # warn only, not always forbidden
  - platicar
  - ahorita
  - boleto # warn depending on context

argentina_over_slang_warn:
  - che
  - boludo
  - laburo
  - quilombo
  - mina
  - pibe
  - guita

bad_voseo_forms:
  - cantastes
  - comistes
  - vivistes
  - habés
  - habís
  - sós
  - vai
  - ite
```

Rules:

```text
hard_forbidden => block or regenerate
warn => LocaleCriticUY returns needs_review
```

Do not make every Argentinian word forbidden. Only flag excessive slang.

---

# 9. Few-shot examples

Implement:

```text
locale_packs/es_uy_montevideo/few_shots_assistant.yaml
```

Starter examples:

```yaml
- id: assistant_invoice_001
  mode: assistant
  input_ru: "Можешь отправить мне счёт?"
  output:
    formal: "Hola, ¿me podría mandar la factura, por favor?"
    friendly: "¿Me podés mandar la factura?"
    simple: "Mandame la factura, por favor."

- id: assistant_card_001
  mode: assistant
  input_ru: "Я хотел уточнить, можно ли оплатить картой."
  output:
    formal: "Hola, quería consultar si se puede pagar con tarjeta."
    friendly: "Te hago una consulta: ¿se puede pagar con tarjeta?"
    simple: "¿Puedo pagar con tarjeta?"

- id: assistant_return_001
  mode: assistant
  input_ru: "Я не понял, должен ли я сам отправить товар или ждать курьера."
  output:
    formal: "Hola, quería confirmar si tengo que enviar el producto por mi cuenta o si pasa alguien a retirarlo."
    friendly: "No me quedó claro si tengo que mandarlo yo o si pasa un cadete a retirarlo."
    simple: "¿Tengo que mandarlo yo o viene alguien a retirarlo?"

- id: assistant_time_001
  mode: assistant
  input_ru: "Да, могу подойти завтра около 10:30."
  output:
    formal: "Sí, puedo pasar mañana alrededor de las 10:30."
    friendly: "Dale, puedo pasar mañana tipo 10:30, si te sirve."
    simple: "Sí, puedo pasar mañana a las 10:30."

- id: assistant_repeat_001
  mode: assistant
  input_ru: "Можешь повторить, пожалуйста?"
  output:
    formal: "¿Me podría repetir, por favor?"
    friendly: "¿Me repetís, por favor?"
    simple: "¿Me repetís?"
```

Implement:

```text
locale_packs/es_uy_montevideo/few_shots_live.yaml
```

```yaml
- id: live_card_001
  input_ru: "Скажите, пожалуйста, можно оплатить картой?"
  output_es: "Disculpe, ¿se puede pagar con tarjeta?"

- id: live_spanish_001
  input_es: "Podés pasar mañana después de las 10?"
  output_ru: "Можешь зайти завтра после 10?"

- id: live_repeat_001
  input_ru: "Можно повторить, пожалуйста?"
  output_es: "¿Me puede repetir, por favor?"

- id: live_dont_understand_001
  input_ru: "Извините, я не понял."
  output_es: "Disculpe, no entendí."
```

Implement:

```text
locale_packs/es_uy_montevideo/few_shots_extraction.yaml
```

```yaml
- id: extraction_invoice_001
  source_es: "¿Me podés mandar la factura mañana?"
  expected_items:
    - item_type: verb_form
      display_text: "vos podés"
      surface_text: "podés"
      lemma: "poder"
      translations_ru: ["ты можешь", "можешь"]
      grammar:
        pronoun: "vos"
        tense: "presente"
        mood: "indicativo"
        person: 2
        number: "singular"
        voseo: true
      governance: ["poder + infinitivo"]

    - item_type: verb_infinitive
      display_text: "mandar"
      surface_text: "mandar"
      lemma: "mandar"
      translations_ru: ["отправлять", "присылать"]
      governance: ["mandar algo a alguien"]

    - item_type: noun
      display_text: "la factura"
      lemma: "factura"
      translations_ru: ["счёт", "квитанция"]
      grammar:
        gender: "feminine"
        number: "singular"
        article: "la"

    - item_type: adverb
      display_text: "mañana"
      translations_ru: ["завтра"]
```

---

# 10. Prompt contracts

## 10.1 Assistant reply prompt

Update `assistant_reply.md`.

Required behavior:

```text
You are Decime UY, a communication translator for Uruguay / Montevideo Spanish.

Return exactly three variants:
- formal
- friendly
- simple

Do not return "recommended", "short", "more_formal", or "what they want".

Use conversation history as context.

Preserve number format:
digits stay digits; words stay words.

If user input mixes Russian/English with Spanish words, preserve Spanish terms when appropriate.

Target output:
natural, concise, locally usable es-UY-montevideo.

Avoid:
Spain-specific vocabulary and grammar,
Mexican/Colombian neutralized wording,
excessive Buenos Aires slang,
vosotros forms.

Use:
Formal: polite, brief, often impersonal/conditional/usted-style.
Friendly: natural WhatsApp style, voseo allowed.
Simple: A1/A2-friendly.
```

Required JSON schema:

```json
{
  "type": "object",
  "properties": {
    "locale_variant": {"type": "string"},
    "formal": {
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["text"]
    },
    "friendly": {
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["text"]
    },
    "simple": {
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["text"]
    }
  },
  "required": ["locale_variant", "formal", "friendly", "simple"]
}
```

## 10.2 Incoming translation prompt

Required behavior:

```text
Translate Spanish input into Russian and optionally English.
Use conversation history for context.
Do not add a separate "what they want" block.
Optional explanation can be generated only if explicitly requested.
Preserve original text exactly as transcript/input.
```

Schema:

```json
{
  "type": "object",
  "properties": {
    "source_language": {"type": "string"},
    "original_text": {"type": "string"},
    "translation_ru": {"type": "string"},
    "translation_en": {"type": "string"},
    "optional_explanation_ru": {"type": "string"}
  },
  "required": ["source_language", "original_text", "translation_ru"]
}
```

## 10.3 Live prompt

Required behavior:

```text
If input is RU/EN, output one brief polite es-UY translation.
If input is ES, output direct RU translation.
No variants.
No long explanation.
```

Schema:

```json
{
  "type": "object",
  "properties": {
    "detected_source_language": {"type": "string"},
    "target_language": {"type": "string"},
    "output_text": {"type": "string"},
    "locale_variant": {"type": "string"}
  },
  "required": ["detected_source_language", "target_language", "output_text"]
}
```

## 10.4 Training extraction prompt

Required behavior:

```text
Extract only atomic training items:
noun, adjective, adverb, verb_form, verb_infinitive.

Do not extract:
expression, sentence_pattern, idiom, collocation, full_phrase.

For verb_form:
- extract exact form as standalone item
- display with pronoun
- include lemma
- include tense, mood, person, number, voseo flag
- include governance if known
- do not automatically add infinitive for each verb form

For nouns:
- include article, gender, number.

For adjectives:
- include gender/number and forms if known.

For adverbs:
- include exact meaning and contextual variants.
```

Allowed enum:

```json
["noun", "adjective", "adverb", "verb_form", "verb_infinitive"]
```

---

# 11. LocaleCriticUY

Implement `locale_critic_uy.py`.

Input:

```python
text: str
context: Literal["assistant_formal", "assistant_friendly", "assistant_simple", "live"]
```

Output:

```python
class LocaleCriticResult(BaseModel):
    status: Literal["ok", "needs_review", "probably_not_uy"]
    issues: list[LocaleIssue]
```

Issue:

```python
class LocaleIssue(BaseModel):
    severity: Literal["block", "warn"]
    code: str
    term: str
    message: str
```

Rules:

### Block

```text
vosotros
vosotras
podéis
tenéis
sois
estáis
habéis
```

### Warn

```text
vale
ordenador
móvil
piso
coger
celular
platicar
ahorita
che
boludo
laburo
quilombo
mina
pibe
guita
```

### Bad voseo warning/block depending on context

```text
cantastes
comistes
vivistes
habés
habís
sós
vai
ite
```

Behavior:

```text
If hard_forbidden found → probably_not_uy
If warn terms found → needs_review
If no issues → ok
```

Do not auto-rewrite in the critic. The caller may regenerate if `probably_not_uy`.

---

# 12. Post-processing rules

After every assistant/live generation:

```text
1. Validate JSON schema.
2. Run LocaleCriticUY on every Spanish output.
3. Check number preservation.
4. If hard forbidden terms are detected, regenerate once.
5. If still bad, return output with needs_review flag.
6. Log issue to event_log.
```

For number preservation:

Implement a helper:

```python
extract_number_like_tokens(text: str) -> list[str]
```

Track:

```text
digits
times
prices
document-like numbers
```

If user input contains `10:30`, output should contain `10:30`, not `diez y media`.

If input contains `diez y media`, output should not force `10:30`.

---

# 13. Eval cases

Implement:

```text
locale_packs/es_uy_montevideo/eval_cases.yaml
```

Starter cases:

```yaml
- id: eval_assistant_001
  task: assistant_reply
  input_ru: "Можешь отправить мне счёт?"
  expected_any:
    - "factura"
  forbidden:
    - "vosotros"
    - "podéis"
    - "vale"

- id: eval_assistant_002
  task: assistant_reply
  input_ru: "Да, могу подойти завтра около 10:30."
  expected_any:
    - "10:30"
  preserve_numbers:
    - "10:30"

- id: eval_assistant_003
  task: assistant_reply
  input_ru: "Я хотел уточнить, можно ли оплатить картой."
  expected_any:
    - "tarjeta"
    - "se puede pagar"
  forbidden:
    - "móvil"
    - "vale"

- id: eval_live_001
  task: live_ru_to_es
  input_ru: "Скажите, пожалуйста, можно оплатить картой?"
  expected_any:
    - "tarjeta"
  forbidden:
    - "vosotros"
    - "vale"

- id: eval_live_002
  task: live_es_to_ru
  input_es: "Podés pasar mañana después de las 10?"
  expected_ru_any:
    - "можешь"
    - "завтра"
    - "после 10"

- id: eval_extraction_001
  task: training_extraction
  source_es: "¿Me podés mandar la factura mañana?"
  expected_items:
    - item_type: verb_form
      display_text: "vos podés"
    - item_type: verb_infinitive
      display_text: "mandar"
    - item_type: noun
      display_text: "la factura"
    - item_type: adverb
      display_text: "mañana"
  forbidden_item_types:
    - expression
    - idiom
    - sentence_pattern
```

Add script:

```text
scripts/eval_es_uy.py
```

Features:

```text
--model qwen3:4b
--base-url http://localhost:11434
--cases locale_packs/es_uy_montevideo/eval_cases.yaml
--output reports/eval_es_uy_qwen3_4b.json
```

Metrics:

```text
json_valid_rate
required_keys_rate
forbidden_terms_count
number_preservation_rate
expected_feature_hit_rate
training_allowed_types_rate
latency_p50_ms
latency_p95_ms
```

---

# 14. Correction dataset collection

Add backend event logging for future fine-tuning.

When user edits a generated variant, store:

```json
{
  "event_type": "assistant_variant_edited",
  "locale_variant": "es-UY-montevideo",
  "source_input": "...",
  "conversation_context": "...",
  "variant": "formal|friendly|simple",
  "model_output": "...",
  "user_edited_output": "...",
  "model": "qwen3:4b",
  "created_at": "..."
}
```

Add optional feedback action later:

```text
No suena uruguayo
Wrong translation
Too formal
Too informal
Too long
```

For this milestone, just store edits if the UI already supports editing.

---

# 15. Implementation tasks for Cursor

## Phase 1 — Locale pack files

Create all locale pack files with content above.

## Phase 2 — Loader

Implement `LocalePackLoader`.

It should load:

```text
style_guide.md
glossary.yaml
forbidden_terms.yaml
few_shots_*.yaml
```

Expose:

```python
get_style_guide(locale_id)
get_glossary(locale_id)
get_forbidden_terms(locale_id)
get_few_shots(locale_id, mode)
```

## Phase 3 — Ollama client update

Update Ollama LLM provider:

```text
support think=false
support format=json schema
support temperature per task
support model from env
support keep_alive
capture latency metrics
```

## Phase 4 — Prompt update

Update prompts to include:

```text
style guide summary
glossary
few-shot examples
forbidden terms
number preservation
schema requirements
/no_think instruction
```

Do not include the entire style guide if prompt becomes too large. Summarize it programmatically.

## Phase 5 — LocaleCriticUY

Implement critic and tests.

## Phase 6 — Postprocessing

Run critic and number preservation checks after outputs.

Regenerate once on block-level violation.

## Phase 7 — Training extraction

Add `adverb` type.

Update schema and tests.

Ensure verb forms do not auto-add infinitive.

## Phase 8 — Eval runner

Implement eval script and baseline report.

## Phase 9 — Docs

Update:

```text
docs/development_brief.md
docs/technical_status_report.md
docs/locale_es_uy.md
docs/model_qwen3_4b.md
```

---

# 16. Acceptance criteria

The task is complete when:

- `qwen3:4b` is configured as the default Ollama model.
- Ollama calls use `think=false` or equivalent non-thinking mode.
- Assistant prompt returns exactly Formal/Friendly/Simple.
- Incoming translation prompt does not return “what they want” block.
- Live prompt returns one output only.
- Training extraction supports adverb.
- Training extraction does not output expressions/idioms/patterns.
- Verb forms display pronoun.
- Verb forms do not auto-create infinitives.
- LocaleCriticUY flags hard Spain-specific forms.
- Number preservation is checked.
- Eval runner exists and can run against Ollama.
- Locale pack files exist and are loaded.
- Docs are updated.

---

# 17. References for developer context

Use these sources only as implementation context, not as runtime dependencies:

- Qwen3 4B model card: https://huggingface.co/Qwen/Qwen3-4B
- Ollama qwen3:4b: https://ollama.com/library/qwen3:4b
- Ollama API structured outputs: https://github.com/ollama/ollama/blob/main/docs/api.md
- RAE DPD voseo: https://www.rae.es/dpd/voseo

