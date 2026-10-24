# Decime UY — Product Task for Cursor

**Purpose:** update the current Decime UY implementation to match the clarified product vision.

**Audience:** Cursor / AI coding agent, product owner, implementation reviewer.

**Status context:** Decime already has separate Quick Reply, Compose, Audio, Training/Review, Android APK/share flow, and partial auth/admin. The next product milestone is not adding more features, but refactoring the product around a clearer UX and preparing it for private VM testing.

---

## 1. Product direction

Decime UY is primarily a **context-aware communication translator for life in Uruguay**, with learning features as a secondary but important layer.

Core product promise:

> Understand what was said. Translate your answer naturally. Use it in real communication. Learn useful words and forms from it.

The current product should be treated as a **private alpha**, not a public SaaS.

---

## 2. Target users for this milestone

### Primary user

A Russian-speaking or English-speaking immigrant / visitor in Uruguay, mostly in Montevideo, who needs to:

- understand Spanish messages;
- answer in natural Uruguayan Spanish;
- communicate in WhatsApp and in person;
- gradually collect useful vocabulary and verb forms.

### Test audience

- Owner/user.
- Up to 5 invited testers.
- No public registration.
- No self-service onboarding.

---

## 3. Hard product decisions already made

### In scope

- Uruguay / Montevideo Spanish only.
- Android-first mobile usage.
- Web admin only.
- VM deployment.
- Postgres persistence.
- Invite-only users.
- Local AI providers preferred.
- Android Share flow.
- Copy/share out to WhatsApp or other apps.
- Training from generated/translated material.
- Self-assessment review, not pronunciation scoring.

### Out of scope

Do not implement or plan for this milestone:

- Twilio.
- Meta WhatsApp API.
- WhatsApp bot.
- Palabra.
- Realtime speech conversation.
- Multi-region Spanish.
- Public registration.
- Payments.
- Marketplace of lists.
- Expression / idiom extraction.
- Pronunciation scoring.
- Full offline mode.
- Admin panel in Android.

---

## 4. Core product model

The product must be refactored from separate modules into two primary user-facing modes:

```text
1. Assistant
   For text/audio communication and replies.

2. Live
   For in-person microphone-first translation.
```

Training and Review remain available, but they are secondary to the communication translator.

---

# 5. Main screen: Assistant

## 5.1 Goal

Assistant is the main communication workflow. It replaces the current split between Quick Reply, Compose and Audio.

It must support:

```text
shared text
pasted text
uploaded audio
shared audio
recorded audio
incoming Spanish message
incoming Spanish audio/transcript
user reply intent in Russian or English
conversation history for the current communication act
translation into Russian/English
reply generation into es-UY
Formal / Friendly / Simple reply variants
actions per variant
Add to training
Start new conversation
```

## 5.2 Core Assistant flow

### Flow A — incoming Spanish text

1. User shares or pastes Spanish text into Decime.
2. Decime stores it as a turn in the current conversation session.
3. Decime translates it into the user's preferred explanation language.
4. User writes their intended response in Russian or English.
5. Decime generates three Spanish reply variants:
   - Formal
   - Friendly
   - Simple
6. User can edit/copy/share/play/add-to-training for each variant.
7. The generated reply and selected variant remain in the current conversation context.

### Flow B — incoming Spanish audio

1. User shares/uploads/records Spanish audio.
2. Decime transcribes it.
3. Decime stores the transcript as the original incoming message.
4. Decime translates it.
5. User writes or records their answer intent in Russian or English.
6. Decime generates Formal / Friendly / Simple Spanish variants.
7. User shares/copies the selected variant.

### Flow C — no incoming message, user wants to say something

1. User types or records an intent in Russian/English.
2. Decime generates Formal / Friendly / Simple es-UY variants.
3. User shares/copies/plays/adds to training.

This replaces the old standalone Compose mode.

---

## 5.3 Conversation history

The assistant must have a current conversation session.

### Required UI

```text
[Start new conversation]
```

### Behavior

- Until the user taps **Start new conversation**, Decime must use the current session history as context.
- The history must include original text in the language in which it was entered.
- For audio, store the transcript as the original text.
- The current session may include:
  - incoming Spanish messages;
  - incoming audio transcripts;
  - translations;
  - user reply intents in RU/EN/mixed text;
  - generated es-UY variants;
  - edited variants;
  - selected/shared/copied variant metadata;
  - training extraction source links.

### Start new conversation behavior

When the user taps **Start new conversation**:

- Clear the active communication context.
- Do not continue using previous context.
- It is acceptable to delete the previous active session history for this milestone.
- Do not archive old conversation sessions unless this is already easy in the persistence layer.
- Training items created from old messages must not be deleted.

---

## 5.4 Translation and explanation

Do not show a separate block like “what the person wants from you”.

The translation itself must be contextual and should be enough.

Optional explanation is allowed only behind a button:

```text
[Explain]
```

The default UI should be compact and communication-oriented.

---

## 5.5 Reply variants

The Assistant must generate exactly three variants:

```text
Formal
Friendly
Simple
```

### Default ordering

The first/default variant is:

```text
Formal
```

### Required actions per variant

Every variant must support the same actions:

```text
Edit
Copy
Share
Play pronunciation
Add to training
```

### Meaning of Play

For this milestone, audio is mainly for learning/pronunciation support. It is not a core requirement to generate an audio file for sending in a chat.

---

## 5.6 Number handling

Add an explicit product rule:

```text
Numbers must preserve the input format.
```

Examples:

```text
Input: 10:30
Output: 10:30

Input: diez y media
Output: diez y media

Input: 1000
Output: 1000

Input: mil
Output: mil
```

If the user enters digits, keep digits.  
If the user enters words, keep words.

This applies especially to:

- times;
- dates;
- prices;
- document numbers;
- addresses;
- quantities.

---

# 6. Separate screen: Live

## 6.1 Goal

Live is for in-person communication.

It should be optimized for speed and microphone use.

It must feel different from Assistant.

## 6.2 Main use cases

### RU/EN voice → Spanish

User speaks into phone:

```text
Скажите, пожалуйста, можно оплатить картой?
```

Decime returns a short, polite, sufficiently formal es-UY phrase.

### Spanish voice/text → RU/EN

User records or enters what another person said in Spanish.

Decime returns translation into the user's preferred language.

## 6.3 Live UX rules

Live must have:

- microphone-first interface;
- text fallback;
- no style variant selector;
- one output only;
- default style: polite, brief, sufficiently formal;
- playback button;
- copy/share if useful;
- optional Add to training;
- minimal UI.

## 6.4 Live style policy

Default output should be:

```text
polite
brief
clear
sufficiently formal
Uruguay / Montevideo Spanish
```

Style customization may be added later, but not in this milestone.

---

# 7. Training

Training remains important, but it is not the primary source of product value in this milestone.

The current extraction logic is directionally correct, but must be adjusted.

## 7.1 MVP training item types

The extraction pipeline must support exactly these atomic types:

```text
noun
adjective
adverb
verb_form
verb_infinitive
```

Add `adverb` if not present yet.

## 7.2 Do not extract in this milestone

Do not extract:

```text
full expressions
sentence patterns
idioms
collocations
full phrase cards
```

These are future features.

## 7.3 Nouns

Nouns should include:

- article;
- gender;
- number;
- exact/contextual translation;
- RU variants;
- EN variants if available;
- example source.

Example:

```text
la factura — счёт / квитанция
```

## 7.4 Adjectives

Adjectives should include:

- surface form;
- lemma;
- gender/number if applicable;
- form variants if known;
- exact/contextual translation;
- example source.

Example:

```text
claro / clara — понятный / понятная / ясный / ясная
```

## 7.5 Adverbs

Adverbs are required.

Examples:

```text
mañana — завтра
después — потом / после
acá — здесь / тут
ahí — там / тут, в зависимости от контекста
todavía — ещё
ya — уже / сейчас / больше не, depending on context
recién — только что / недавно
```

## 7.6 Verb forms

Verb forms must be treated as standalone training items.

Examples:

```text
vos podés
yo voy
yo puedo
vos querés
```

Each verb form must include:

- displayed form with pronoun;
- exact surface form;
- lemma;
- tense;
- mood;
- person;
- number;
- voseo flag if relevant;
- governed preposition / pattern if known;
- exact/contextual RU translation;
- EN translation if available;
- example source.

### Important rule

Do not automatically add infinitive cards when a verb form is extracted.

Example:

If source contains:

```text
podés
```

Suggest:

```text
vos podés
```

Do not automatically add:

```text
poder
```

unless the source contains it or the user explicitly adds it.

## 7.7 Pronouns

Object pronouns are not separate cards yet.

They may remain in examples or in verb/pattern metadata.

Do not create standalone cards for:

```text
me
te
lo
la
se
```

unless specifically required later.

## 7.8 Review

Review remains self-assessment only.

Keep:

```text
show → recall → user rates Again / Hard / Good / Easy
```

Do not implement STT pronunciation scoring in this milestone.

## 7.9 Deletion

Training must support deletion of cards.

History deletion must not delete training items.

---

# 8. Data and privacy product rules

## 8.1 What to store

Store current communication history because it is needed for contextual translation.

Store:

- original text in original language;
- Spanish audio transcripts;
- user reply intents;
- generated variants;
- selected/edited variant;
- training items created from the material.

## 8.2 No “process without saving” mode

Do not implement a “do not save this message” mode in this milestone.

## 8.3 Destructive actions

Separate destructive actions:

```text
Clear current conversation
Delete training item
Delete training list
Clear history, if retained
Clear audio cache, if exposed
```

Do not let “clear history” delete training.

---

# 9. Admin and users

## 9.1 User model

- Invite-only.
- Up to 5 users for alpha.
- All normal users are equal.
- Admin is not a normal product user.
- Admin only manages the service and user accounts.

## 9.2 Admin UI

Admin UI is web-only.

Do not build admin screens into Android.

## 9.3 Admin features for this milestone

Required:

```text
login as admin
create user
disable user
reset/change password
view user list
```

Not required now:

```text
usage analytics
viewing user content
admin dashboard in Android
billing
roles beyond admin/user
```

---

# 10. Mobile / Android product rules

## 10.1 Android is the primary test client

Android APK should be the main daily-use client.

## 10.2 Share-in

Support:

```text
text/plain
audio/*
```

from Android Share flow.

## 10.3 Share-out

Support sharing generated text back through Android Share.

Prefer adding a specific “Share to WhatsApp” button if easy, but keep generic Share as fallback.

Do not send messages automatically.

## 10.4 API URL

For this milestone, Android should use one production API URL.

Do not optimize for LAN/local-PC mode anymore.

Settings override may remain for development, but should not be prominent in the user flow.

---

# 11. VM / deployment product requirement

The product must be usable from a VM over HTTPS.

The VM version is the primary test environment.

Local PC mode is no longer a product requirement.

---

# 12. Acceptance criteria

## Assistant acceptance

- User can open Assistant on Android.
- User can share Spanish text into Decime.
- Decime shows contextual translation.
- User can write reply intent in Russian/English/mixed text.
- Decime generates Formal / Friendly / Simple es-UY variants.
- Formal appears first.
- User can edit each variant.
- User can copy each variant.
- User can share each variant.
- User can play pronunciation for each variant.
- User can add each variant to training.
- Current conversation history is used for follow-up translations.
- Start new conversation clears active context.

## Audio acceptance

- User can upload or share Spanish audio.
- Decime transcribes it.
- Decime stores transcript as original input.
- Decime translates transcript.
- User can reply from that context.
- Live supports microphone input.
- Live supports Spanish audio input for understanding another person.

## Training acceptance

- Extraction supports noun, adjective, adverb, verb_form, verb_infinitive.
- Extraction does not create full expressions/idioms/sentence pattern cards.
- Verb forms display pronoun.
- Infinitives are not auto-added for verb forms.
- User can delete training cards.
- Review remains self-assessment only.

## Multi-user acceptance

- Users are invite-only.
- Admin can create/disable users from web.
- Normal users cannot see each other’s conversations, training items, transcripts, audio metadata, or history.
- Admin is not shown as a normal product user in Android.

## Deployment acceptance

- Service runs on VM over HTTPS.
- Android APK uses the VM URL by default.
- Postgres is the runtime database.
- Data survives API restarts.
- Manual backup procedure exists.

---

# 13. Product implementation order

1. Update docs and navigation around the new model.
2. Implement conversation sessions.
3. Refactor Quick Reply + Compose + Audio into Assistant.
4. Implement Formal/Friendly/Simple variants.
5. Implement Live screen.
6. Add `adverb` training item type.
7. Fix history/training destructive behavior.
8. Prepare for Postgres/auth/user-isolation technical milestone.
9. Update Android to production URL behavior.
10. Run phone QA.

---

# 14. Cursor instruction

When implementing this product task:

- Do not add unrelated features.
- Do not implement Twilio, Palabra, WhatsApp bot or realtime speech.
- Preserve working code where possible.
- Refactor UI toward the new Assistant/Live model.
- Keep current API contracts if possible, but add new endpoints if needed for sessions.
- Add tests for changed behavior.
- Update documentation after implementation.

