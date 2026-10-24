# Decime UY — QA Checklist

**Version:** 0.2  
**Last updated:** 2026-06-23

---

## Manual QA — Generated replies

For every generated reply, verify:

- [ ] Sounds natural in Uruguay
- [ ] Not too Spain-like
- [ ] Not too Buenos Aires slangy
- [ ] A1/A2-friendly when requested
- [ ] Translation faithful to user intent
- [ ] Tone appropriate for channel
- [ ] Would send this in WhatsApp

---

## Manual QA — Extracted candidates

- [ ] Noun article correct
- [ ] Gender correct
- [ ] Verb form exact (not replaced by infinitive)
- [ ] Pronoun correct
- [ ] Tense/mood plausible
- [ ] Translations accurate and contextual
- [ ] Item worth learning

---

## Forbidden pattern warnings (Uruguay focus)

These should trigger warnings in generated output:

```text
vosotros
vale
móvil
ordenador
coger
```

---

## Seed test scenarios

Test compose and extraction against:

- Mercado Libre return
- Asking if card payment is accepted
- Asking for address/time
- Doctor appointment
- Delivery coordination
- Rent/apartment visit
- Neighbor small talk

---

## End-to-end MVP acceptance

1. Paste or upload WhatsApp message/audio
2. See transcript/meaning (Quick Reply **Translate** or STT)
3. Generate Uruguay-ready reply
4. Hear the reply
5. Copy for WhatsApp (web) or Share (Android)
6. Click "Add to training"
7. See candidate nouns/adjectives/verb forms/infinitives
8. Approve selected candidates
9. Review later with audio and active recall

---

## Android / LAN (Phase 5)

- [ ] APK installs and opens Quick Reply
- [ ] Share text from WhatsApp prefills incoming field
- [ ] Share audio transcribes (or fallback: upload)
- [ ] Settings: LAN scan finds PC API (`--host 0.0.0.0`)
- [ ] Diagnostics: health OK, translate test OK
- [ ] Share generated reply back to WhatsApp

See [android_setup.md](android_setup.md), `scripts/android_qa.ps1`.

---

## Auth (Phase 6, when `AUTH_ENABLED=true`)

- [ ] Login at `/login/` returns JWT
- [ ] Protected API returns 401 without token
- [ ] Admin can create/disable users at `/app/admin/users/`
- [ ] Android stores token and sends `Authorization` header

See [vm_auth.md](vm_auth.md).

---

## Native review (before external users)

Have 1–2 Uruguay/Montevideo native speakers review:

- Base training lists
- 20 common generated replies
- Audio naturalness
- Tone labels
