# Out of scope (product plans)

**As of 2026-06:** the following are **not planned** for Decime UY. Do not add tasks, env vars, or dependencies for them unless the owner explicitly reopens them.

## Twilio / Meta WhatsApp API

- No WhatsApp bot, webhooks, or Sandbox integration.
- WhatsApp UX = **system Share** on Android + copy/paste on web (Phase 5).

## Palabra.ai

- No Palabra STT/TTS provider.
- Speech stack = **OpenAI** (cloud) + **local Whisper / Orpheus** (see `.env` and [local_stt_setup.md](local_stt_setup.md), [orpheus_tts_setup.md](orpheus_tts_setup.md)).

## What we use instead

| Need | Approach |
|------|----------|
| Incoming WhatsApp text/audio | Capacitor `ACTION_SEND`, clipboard, file upload |
| Outgoing reply | `@capacitor/share`, copy to clipboard |
| STT / TTS | `faster_whisper`, Orpheus, OpenAI — via `STT_PROVIDER` / `TTS_PROVIDER` |

Historical mentions in older brief sections are archived context only; see git history if needed.
