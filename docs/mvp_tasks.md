# Decime UY — MVP Tasks

**Last updated:** 2026-06-24  
**Status:** Phases 0–7 done; production on `decime.online`; pre-beta polish in progress

---

## Phase 0 ✅ | Phase 1 ✅

See git history / conversation log.

---

## Phase 2 — Audio STT/TTS ✅

- [x] `POST /api/v1/audio/transcribe` (Fake + OpenAI STT)
- [x] `POST /api/v1/audio/synthesize` with TTS cache by hash
- [x] `GET /api/v1/audio/files/{id}` for playback
- [x] `DELETE /api/v1/history` clears compose history + audio cache
- [x] Frontend `/app/audio` upload + transcribe
- [x] **Play audio** on Compose reply card
- [x] `SPEECH_PROVIDER` in config
- [x] Local storage `data/audio/`
- [x] Tests (17 passing)

---

## Phase 3 — Add to training ✅

- [x] `POST /api/v1/training/extract-candidates` (Fake + OpenAI)
- [x] `POST /api/v1/training/approve-candidates` (+ optional TTS per item)
- [x] `GET /api/v1/training/lists`, `GET /api/v1/training/items`
- [x] Approval UI on Compose (`Add to training`)
- [x] `/app/training` — saved phrases list
- [x] In-memory training repo + canonical keys / duplicate detection
- [x] Tests (24 passing)

---

## Phase 4 — Review + SRS ✅

- [x] `GET /api/v1/training/review/next` — due queue with review modes
- [x] `POST /api/v1/training/review/submit` — grade + SRS scheduling
- [x] Scheduler: Again / Hard / Good / Easy (0 → 10m → 1d → 3d → 7d → 14d → 30d)
- [x] Review modes: RU→ES, ES→RU/EN, audio→meaning, grammar prompt
- [x] `/app/training/review` — review session UI
- [x] Due count on `/app/training` + Review now
- [x] Tests (34 passing)

---

## Phase 5 — WhatsApp / Quick Reply ✅ (web) + Android scaffold ✅

- [x] `/app/quick-reply` — paste text/audio from clipboard, translate incoming, generate reply
- [x] `POST /api/v1/incoming/understand-text` — single translation, no redundant meaning
- [x] Copy for WhatsApp (web) / Share to WhatsApp (Android shell)
- [x] Capacitor Android project (`apps/web/android`)
- [x] Incoming `ACTION_SEND` for `text/plain` and `audio/*`
- [x] Outgoing share via `@capacitor/share`
- [x] `/app/settings/`, `/app/diagnostics/` — LAN API setup on phone
- [ ] Real-device QA (WhatsApp share in/out, HTTPS API) — see [docs/android_setup.md](android_setup.md)
- [x] Tests (48 passing — includes auth, incoming, user isolation)

---

## Phase 6 — Auth / VM ✅

- [x] `AUTH_ENABLED` + JWT (HS256) on protected routes
- [x] SQLite user store (local) / Postgres `app_users` (when `DATABASE_URL`)
- [x] `POST /api/v1/auth/login`, register, admin user CRUD
- [x] Frontend: `/login/`, `AuthGate`, `/app/admin/users/`
- [x] Android: token in Capacitor Preferences + native HTTP headers
- [x] `scripts/create_admin.py`, bootstrap admin via env
- [x] Per-user isolation when Postgres enabled
- [x] `deploy/` Docker Compose (Caddy + api + postgres + static web)
- [x] Production: `https://decime.online`, `https://api.decime.online`
- [x] E2E smoke test (`scripts/vm_internal_e2e.py`) — 14 checks on VM
- [ ] Real-device QA against HTTPS VM — see [deploy/README.md](../deploy/README.md)

See [docs/vm_auth.md](vm_auth.md).

---

## Phase 7 — Persistence (Postgres) ✅

- [x] `PostgresTrainingRepository`, `PostgresHistoryRepository`, `PostgresUserStore`
- [x] Migration `003_unified_users.sql` — `app_users` canonical FK
- [x] Auto-migrations on startup; `event_log` for analytics
- [x] Per-user default training list on signup
- [x] User-scoped audio paths (`data/audio/{user_id}/`)
- [x] Tests (48 passing, includes user isolation)

---

## Phase 8 — Pre-beta polish 🚧

- [x] Live Chat (`/app/live`) — mic + text, auto ES↔RU/EN
- [x] Web microphone device selector in Live Chat
- [x] Android production APK: default `https://api.decime.online`, full nav (Training, History)
- [x] Quick Reply UI in English; tone selector (Neutral / Friendly / Simple)
- [x] Nav: Compose/Audio removed → Live Chat; legacy routes redirect
- [x] Training extract fix (`build_canonical_key` import); locale FK fix
- [x] Play audio with JWT; Regenerate button
- [x] Training panel: Retry + wait message during extract
- [ ] Unified Assistant UX (product task)
- [ ] Onboarding; hide diagnostics in prod mobile
- [ ] Device QA on physical phone

## Out of scope (not in roadmap)

See [out_of_scope.md](out_of_scope.md).

- **Twilio** / Meta WhatsApp API — no bot or webhooks
- **Palabra.ai** — no third-party speech provider; use OpenAI + local Whisper/Orpheus only
