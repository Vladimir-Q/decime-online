# Decime UY — Cursor Working Rules

Project: **Decime UY**.

Read `docs/product_brief.md` and `docs/development_brief.md` before coding.

Build only MVP features unless explicitly asked.

Prefer small, testable changes.

Use typed schemas and structured LLM outputs.

Keep providers replaceable (STT, TTS, LLM behind interfaces).

Do not hardcode OpenAI directly into business logic.

Do not auto-add training items without user approval.

For learning items, `surface_text` is the primary memorized form; `lemma` is metadata.

Keep Uruguay/Montevideo as the only active target locale in MVP.

Avoid full expression extraction in MVP.

After each coding step, provide validation commands and expected results.

## Session continuity

Before the context window ends, or after any meaningful decision or implementation:

1. Update **`docs/project_state.md`** — current phase, what exists, next task, open items (keep it short enough for one context).
2. Update **`docs/mvp_tasks.md`** if tasks were completed or reprioritized.
3. Optionally append to local-only **`docs/conversation_log.md`** (gitignored; not published).

In a new session, read **`docs/project_state.md`** first, then dive into briefs/contracts as needed.
