# Decime UY — Product Brief

**Version:** 0.1  
**Date:** 2026-05-16  
**Owner:** Vladimir Karataev  
**MVP geography:** Uruguay, Montevideo-first  
**MVP user input languages:** Russian and English first; Spanish supported for understanding, correction and extraction  
**MVP target output:** natural, polite-neutral, A1/A2-friendly Uruguayan Spanish for real-life communication

> **Shipped UX (2026-10):** Quick Reply / Live Chat produce **one** es-UY reply with tone selection (Recommended / Simple A2), not a set of parallel reply variants. For current screens and deploy steps see [../README.md](../README.md) and [project_state.md](project_state.md).

---

## 1. One-line product definition

**Decime UY is a context-aware Uruguayan Spanish communication and learning copilot for immigrants: it helps users understand, write, hear, practice and remember real-life replies for WhatsApp and in-person communication in Montevideo.**

The product is not a generic language course and not a generic translator. It connects immediate communication help with structured language learning.

```text
Real-life situation → context-aware Uruguayan Spanish answer → audio → add to training → recall practice → real-life use
```

---

## 2. Product thesis

The target user does not want to first complete a full Spanish course and only then start communicating. They need to communicate now, but they also want each real interaction to become learning material.

The product should solve two jobs at the same time:

1. **Use it now:** understand a message, compose a reply, say something in person, generate or hear audio.
2. **Learn it for later:** extract useful words and verb forms from real messages and generated replies, save them into personal lists, listen, recall and repeat until speech becomes faster.

The core product promise:

> **Answer now. Learn from every answer. Speak faster next time.**

---

## 3. Product name and positioning

### Main name

**Decime**

### MVP mode / regional label

**Decime UY**

### Recommended English positioning

**Uruguayan Spanish Communication Copilot**

### Recommended Russian positioning

**AI-помощник для уругвайского испанского: помогает понимать, отвечать и тренировать реальные слова и формы для WhatsApp и живого общения в Монтевидео.**

### Why “Decime”

“Decime” is a Rioplatense/Uruguayan form meaning “tell me.” It fits the user intent better than “Decilo” because the user usually comes with a situation:

- “Tell me what they said.”
- “Tell me how to answer.”
- “Tell me how to say this naturally.”
- “Tell me what words/forms from this message I should learn.”

---

## 4. Primary target user

### MVP target persona

Adult immigrant or long-term resident in Uruguay, especially Montevideo, who:

- speaks Russian natively and/or English at a high level;
- has Spanish around A1–A2 or uneven beginner/intermediate knowledge;
- lives in a Spanish-speaking environment but avoids interaction because of slow recall and fear of errors;
- needs WhatsApp and everyday communication more than classroom grammar;
- wants a practical personal learning loop, not abstract drills;
- has limited study time, around 10 hours/week or less.

### Initial personal use case

The first user is the product owner himself:

- native Russian;
- English C1;
- Spanish around A2 but uneven;
- lives in Montevideo;
- wants Uruguayan Spanish, not generic Latin American Spanish;
- wants to reduce delays in recalling words, verb forms and basic grammar while speaking.

---

## 5. Problem statement

### Main problem

The user receives or needs to send real messages in Spanish but cannot quickly formulate a natural answer. Existing tools do not fully solve this:

- generic translators may produce grammatically correct but contextually unnatural output;
- generic AI tutors are too broad and not tied to real communication;
- Duolingo-like drills do not convert directly into the user’s WhatsApp or in-person needs;
- Anki-like systems require manual card creation and do not understand local context;
- local Uruguayan/Montevideo Spanish is not consistently handled by generic tools.

### Specific pain points

1. **Reply anxiety:** “I understand partially, but I don’t know how to answer naturally.”
2. **Voice-note anxiety:** “Someone sent me an audio; I need the meaning and a reply.”
3. **In-person freeze:** “I know the words, but cannot recall them quickly enough.”
4. **Dialect uncertainty:** “Will this sound local in Uruguay or weird/bookish/Mexican/Spanish?”
5. **Grammar recall lag:** “I know `ir`, but I need `voy`; I know `poder`, but I need `vos podés`.”
6. **Manual learning friction:** “I want useful words/forms from real life to become training cards automatically.”

---

## 6. Core product idea

Decime UY has three core modes.

### Mode 1 — Reply

For incoming messages or real communication contexts.

User provides:

- incoming WhatsApp text;
- incoming WhatsApp audio;
- a description of what they want to answer;
- a live situation like “I need to ask if I can pay by card.”

Product outputs:

- short explanation of meaning;
- recommended reply in Uruguayan Spanish;
- simpler version;
- more polite/formal version if needed;
- audio pronunciation;
- optional “add to training.”

### Mode 2 — Translate / Say it naturally

For user’s own intent in Russian or English.

User writes or says:

> “I want to politely ask whether I have to send the product myself or wait for a courier.”

Product outputs:

- natural Uruguayan Spanish version;
- A1/A2-friendly version;
- WhatsApp-ready version;
- explanation of tone and key choices;
- audio;
- optional training extraction.

### Mode 3 — Train

For structured repetition.

User can:

- create personal lists;
- use base lists;
- add items manually;
- add items extracted from WhatsApp/text/voice/generated replies;
- practice RU/EN → ES, ES → RU/EN, audio → meaning, and grammar prompts;
- hear pronunciation;
- track progress and review schedule.

---

## 7. MVP scope

### MVP name

**Decime UY MVP**

### MVP focus

The MVP should prove the loop:

```text
Input from real life → useful Uruguayan Spanish output → audio → extract atomic learning items → approve → train
```

### Must-have MVP features

1. **Text input RU/EN/ES**
   - User types own phrase or incoming message.
   - Source language auto-detected or selected manually.

2. **Audio input RU/EN/ES**
   - User records or uploads audio.
   - MVP must support user’s own voice and WhatsApp voice-note upload/copy flow.

3. **Context-aware output**
   - Channel: WhatsApp text, WhatsApp voice, in-person, support chat.
   - Tone: neutral, polite-neutral, friendly, firm-but-not-rude, simple A1/A2.
   - Locale: Uruguay / Montevideo.

4. **Smart reply composer**
   - Not just translation; generate what the user should answer.
   - Output must be natural in Uruguay and usable in real communication.

5. **Audio pronunciation**
   - Generate audio for Spanish output and training items.
   - Store/cache generated audio.

6. **Add to training**
   - Any generated or transcribed Spanish text can be turned into training candidates.
   - MVP extraction is atomic: nouns, adjectives, verb forms, infinitives.

7. **Training lists**
   - Personal lists.
   - Base lists.
   - List selection during “add to training.”

8. **Review modes**
   - RU/EN → ES active recall.
   - ES → RU/EN recognition.
   - Audio → meaning.
   - Grammar prompt for nouns/adjectives/verbs.

9. **Simple spaced repetition**
   - new → 10 minutes → 1 day → 3 days → 7 days → 14 days → 30 days.
   - Again / Hard / Good / Easy buttons.

10. **History**
   - Store source input, generated Spanish, extracted items and training status.

---

## 8. Explicit non-goals for MVP

Do not build in MVP:

- a full Spanish course;
- full grammar curriculum;
- all Spanish dialects;
- real-time live conversation with interruption handling;
- production WhatsApp Business integration;
- Android custom keyboard;
- WhatsApp Web extension;
- payments;
- public multi-user marketplace;
- social features;
- full expression/idiom extraction;
- automatic generation of all conjugation tables;
- fine-tuning;
- RAG over large language-learning content.

The MVP must stay narrow and usable.

---

## 9. Locale and dialect policy

### MVP locale

```yaml
target_language: Spanish
target_locale: es-UY-montevideo
country: Uruguay
region: Montevideo
style: natural, polite-neutral, low-slang, locally usable
```

### Output policy

The system must avoid:

- Spain-specific vocabulary unless explicitly requested;
- Mexican/Colombian neutralized phrasing if it sounds unnatural locally;
- excessive Buenos Aires slang;
- overly formal textbook Spanish;
- generic “Latin American Spanish” when a more natural Uruguay-ready variant is possible.

The system may use:

- `vos` forms when natural;
- `ustedes` for plural “you”;
- Montevideo-friendly polite formulas;
- local everyday terms where appropriate.

### Dialect stamp in UI

Every generated answer should show a compact metadata line:

```text
🇺🇾 Uruguay · Montevideo · WhatsApp · neutral amable · A2-friendly
```

---

## 10. User input languages

### Primary input languages

- Russian
- English

### Supported input language

- Spanish

### Expected behavior by input language

#### Russian or English input

The system should treat the input as the user’s intended meaning and produce natural Uruguayan Spanish.

Example:

```text
RU: Я хочу уточнить, можно ли оплатить картой.
ES-UY: Quería consultar si se puede pagar con tarjeta.
```

#### Spanish input

The system should:

- explain meaning in Russian/English;
- optionally normalize to Uruguayan Spanish;
- extract training items from the Spanish text;
- not rewrite unnecessarily if the original is already natural.

---

## 11. Key UX flows

## Flow A — User wants to answer a WhatsApp text

1. User pastes incoming message.
2. User optionally adds “I want to answer that…” in Russian or English.
3. User selects/keeps default context: WhatsApp, polite-neutral, Uruguay/Montevideo.
4. System shows:
   - meaning of incoming message;
   - recommended reply;
   - shorter reply;
   - more polite reply;
   - audio button;
   - copy button;
   - add to training button.
5. User copies answer to WhatsApp.
6. User optionally adds words/forms to training.

## Flow B — User receives a WhatsApp voice note

1. User uploads/forwards/saves audio into Decime.
2. System transcribes.
3. System shows transcript and translation/explanation.
4. User clicks “Help me reply.”
5. System generates a reply from user’s perspective.
6. User can:
   - copy text;
   - play audio;
   - save generated reply as audio reference;
   - add items to training.

## Flow C — User wants to say something in person

1. User types or speaks in RU/EN: “How do I ask if they accept card?”
2. System outputs:
   - short natural Spanish;
   - even simpler version;
   - audio slow / normal;
   - key training candidates.
3. User listens and repeats.
4. User saves selected words/forms.

## Flow D — Add to training from any source

1. User clicks “Add to training” after translation/transcription/reply generation.
2. System extracts candidate items.
3. User sees approval screen grouped by type:
   - nouns;
   - adjectives;
   - verb forms;
   - infinitives.
4. User selects list.
5. User confirms selected items.
6. System generates audio and schedules reviews.

## Flow E — Training session

1. User selects “Review now.”
2. System shows due cards.
3. Card types:
   - RU/EN → ES;
   - ES → RU/EN;
   - Audio → meaning;
   - Grammar prompt.
4. User answers mentally/textually/voice later.
5. User grades answer.
6. System updates next review time.

---

## 12. Training item philosophy

### MVP rule

**Do not extract full expressions in MVP. Extract atomic learning units.**

The learning system must focus on:

1. nouns with article and gender;
2. adjectives with gender/forms;
3. exact verb forms with pronoun, tense, mood and governance;
4. verb infinitives with governance.

### Why not full expressions yet

Full expressions are valuable but add complexity:

- phrase boundary detection;
- idiomatic vs compositional meaning;
- too many candidates;
- harder deduplication;
- harder review UX.

For MVP, atomic items are enough and easier to validate.

---

## 13. Training item types

## 13.1 Noun

A noun must be stored and trained with article and gender.

Example:

```yaml
item_type: noun
surface_text: la factura
lemma: factura
article: la
gender: feminine
number: singular
translations_ru:
  - счёт
  - квитанция
translations_en:
  - bill
  - invoice
context_translation_ru: счёт / квитанция на оплату
example_es: ¿Me podés mandar la factura?
locale_variant: es-UY-montevideo
```

Training prompt:

```text
RU: счёт / квитанция
Expected: la factura
```

The answer should require the article.

## 13.2 Adjective

Adjectives must store surface form, lemma, gender, number and forms where useful.

Example:

```yaml
item_type: adjective
surface_text: claro
lemma: claro
display_text: claro / clara
gender: masculine
number: singular
forms:
  masculine_singular: claro
  feminine_singular: clara
  masculine_plural: claros
  feminine_plural: claras
translations_ru:
  - ясный
  - понятный
translations_en:
  - clear
  - understandable
context_translation_ru: понятный / ясный
example_es: No me queda claro.
```

For invariant/common-gender adjectives:

```yaml
surface_text: importante
display_text: importante / importantes
gender: common
forms:
  singular: importante
  plural: importantes
```

## 13.3 Verb form

A verb form is a separate item from the infinitive.

Key rule:

```text
voy ≠ ir
podés ≠ poder
querés ≠ querer
mandame ≠ mandar
```

Example:

```yaml
item_type: verb_form
surface_text: podés
display_text: vos podés
lemma: poder
pronoun: vos
person: 2
number: singular
tense: presente
mood: indicativo
voseo: true
translations_ru:
  - ты можешь
  - можешь
translations_en:
  - you can
  - you are able to
governance:
  - poder + infinitivo
example_es: ¿Me podés mandar una foto?
```

Example with `voy`:

```yaml
item_type: verb_form
surface_text: voy
display_text: yo voy
lemma: ir
pronoun: yo
person: 1
number: singular
tense: presente
mood: indicativo
translations_ru:
  - я иду
  - я еду
  - я собираюсь
translations_en:
  - I go
  - I am going
  - I am going to
governance:
  - ir a + lugar
  - ir a + infinitivo
example_es: Voy a pasar mañana.
```

## 13.4 Verb infinitive

Infinitives are also trainable, but separately.

Example:

```yaml
item_type: verb_infinitive
surface_text: mandar
lemma: mandar
translations_ru:
  - отправлять
  - посылать
  - присылать
translations_en:
  - to send
governance:
  - mandar algo a alguien
example_es: ¿Me podés mandar una foto?
```

---

## 14. Add to training candidate screen

### Candidate grouping

Candidates should be grouped like this:

```text
Add to training

List: [WhatsApp / реальные сообщения ▼]

☑ Nouns
☑ Adjectives
☑ Verb forms
☑ Infinitives

Candidates:
[✓] noun         la factura      счёт / квитанция        feminine
[✓] verb_form    vos podés       ты можешь / можешь       present, voseo
[✓] infinitive   mandar          отправлять / присылать   mandar algo a alguien
[ ] adjective    claro/clara     понятный / ясный         masc/fem

[Add selected]
```

### Candidate statuses

Each candidate can be:

- `new` — not seen before;
- `learning` — already in user’s active training;
- `known` — user marked as known;
- `ignored` — user does not want to learn it;
- `duplicate_possible` — possible duplicate because translation/grammar is close but not exact.

---

## 15. Base training lists for MVP

The MVP should include curated starter lists. They should be small and useful, not encyclopedic.

### List 1 — Survival Uruguay A1/A2 nouns

Examples:

- la factura — bill / invoice / счёт / квитанция
- el recibo — receipt / квитанция
- la dirección — address / адрес
- el horario — schedule / opening time / расписание / время
- el trámite — procedure / paperwork / процедура / оформление
- el pedido — order / заказ
- la devolución — return / возврат
- la tarjeta — card / карта
- el efectivo — cash / наличные
- la cédula — ID card / удостоверение личности

### List 2 — Basic adjectives

- claro/clara — clear / понятный
- correcto/correcta — correct / правильный
- disponible — available / доступный
- necesario/necesaria — necessary / необходимый
- posible — possible / возможный
- abierto/abierta — open / открытый
- cerrado/cerrada — closed / закрытый

### List 3 — Voseo verb forms, present

- vos sos — you are / ты есть
- vos estás — you are / ты находишься
- vos tenés — you have / у тебя есть / ты должен
- vos podés — you can / ты можешь
- vos querés — you want / ты хочешь
- vos hacés — you do / ты делаешь
- vos venís — you come / ты приходишь
- vos decís — you say / ты говоришь
- vos mandás — you send / ты отправляешь
- vos necesitás — you need / тебе нужно

### List 4 — First-person high-frequency forms

- yo soy — I am
- yo estoy — I am
- yo tengo — I have
- yo puedo — I can
- yo quiero — I want
- yo voy — I go / I am going
- yo necesito — I need
- yo entiendo — I understand
- yo mando — I send
- yo paso — I pass by / I come by

### List 5 — Imperatives with `vos`

- decime — tell me
- mandame — send me
- avisame — let me know
- esperame — wait for me
- pasame — pass/send me
- explicame — explain to me
- confirmame — confirm for me
- ayudame — help me
- repetíme — repeat to me

---

## 16. Review modes in MVP

### Mode 1 — RU/EN → ES active recall

Example:

```text
RU: счёт / квитанция
Expected: la factura
```

### Mode 2 — ES → RU/EN recognition

Example:

```text
ES: vos podés
Expected: ты можешь / можешь
```

### Mode 3 — Audio → meaning

User hears audio and recalls the meaning.

Example:

```text
Audio: la factura
Expected: счёт / квитанция
```

### Mode 4 — Grammar prompt

For nouns:

```text
RU: счёт
Prompt: noun + article
Expected: la factura
```

For adjectives:

```text
RU: понятная
Prompt: feminine singular
Expected: clara
```

For verbs:

```text
RU: ты можешь
Prompt: vos + poder + presente
Expected: vos podés
```

---

## 17. Measurement and product success metrics

### Personal success metrics

The product is successful for the first user if after 4–8 weeks:

- user regularly uses it for WhatsApp and live phrases;
- user has 100–300 approved training items;
- user can actively recall frequent forms within 3–5 seconds;
- user starts using at least some generated phrases in real life;
- the tool reduces communication anxiety.

### MVP usage metrics

Track:

- number of translation/reply requests;
- number of audio inputs;
- number of generated audio outputs;
- number of “Add to training” clicks;
- candidate acceptance rate;
- number of approved items;
- daily/weekly review count;
- review correctness;
- self-rated difficulty;
- copied-to-WhatsApp count;
- repeated items with latency under 5 seconds.

### Quality metrics

Track manually at first:

- does the output sound natural in Uruguay;
- does it avoid Spain/Mexico/Buenos Aires over-flavoring;
- are translations accurate;
- are verb forms correctly labeled;
- are noun genders correct;
- is audio understandable and not too artificial;
- does the UI reduce effort rather than add effort.

---

## 18. MVP roadmap

### Phase 0 — Briefs, repository and architecture

Deliverables:

- product brief;
- development brief;
- repo structure;
- basic frontend/backend skeleton;
- database schema draft;
- prompt contracts.

### Phase 1 — Text smart translator / reply composer

Deliverables:

- RU/EN/ES text input;
- context selector;
- structured output;
- recommended reply;
- variants;
- explanation;
- history.

### Phase 2 — Audio input/output

Deliverables:

- record/upload audio;
- transcribe;
- generate reply from transcript;
- generate TTS audio;
- cache audio.

### Phase 3 — Add to training v1

Deliverables:

- extract nouns/adjectives/verb forms/infinitives;
- approval screen;
- deduplication;
- save to list;
- generate item audio.

### Phase 4 — Review mode v1

Deliverables:

- list view;
- due queue;
- RU/EN → ES;
- ES → RU/EN;
- audio → meaning;
- grammar prompt;
- simple SRS.

### Phase 5 — WhatsApp convenience

Deliverables:

- copy-to-WhatsApp UX;
- upload voice note flow;
- Android Share in/out (no Twilio bot — see [out_of_scope.md](out_of_scope.md)).

---

## 19. MVP acceptance criteria

The MVP is acceptable when the user can complete this scenario end-to-end:

1. Paste or upload a WhatsApp message/audio.
2. See transcript/meaning.
3. Generate a natural Uruguay-ready reply.
4. Hear the reply.
5. Copy it for WhatsApp.
6. Click “Add to training.”
7. See candidate nouns/adjectives/verb forms/infinitives.
8. Approve selected candidates.
9. Review them later with audio and active recall.

---

## 20. Risks

### Product risks

- The system may become too broad and lose its core use case.
- Training extraction may overgenerate low-value cards.
- User may prefer instant replies and skip learning.
- Dialect quality may be inconsistent without native review.
- Generated audio may not sound sufficiently Uruguayan.

### Mitigations

- Keep MVP Uruguay/Montevideo only.
- Make candidates user-approved, not auto-added.
- Keep extraction atomic in MVP.
- Add native-speaker QA for seed lists and common outputs.
- Cache approved audio and phrase outputs.
- Track candidate acceptance rate and review retention.

---

## 21. External source notes

These sources inform technical feasibility and constraints. They are not product requirements by themselves.

- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- OpenAI Speech to Text: https://platform.openai.com/docs/guides/speech-to-text
- OpenAI Text to Speech: https://platform.openai.com/docs/guides/text-to-speech
- Supabase Docs: https://supabase.com/docs
- Next.js Docs: https://nextjs.org/docs/app/getting-started
- FastAPI Docs: https://fastapi.tiangolo.com/
