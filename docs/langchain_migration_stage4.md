# Stage 4 — Training extract / normalize via LangChain

**Date:** 2026-10-15  
**Status:** Implemented behind `LLM_ORCHESTRATOR=langchain` (default **`legacy`**)

---

## Scope

| Method | OpenAI | Ollama | Post-process (unchanged) |
|--------|--------|--------|---------------------------|
| `extract_candidates` | LC structured | LC structured | `_parse_extraction_bundle` (IDs, filters, locale) |
| `normalize_dictionary_row` | LC structured | LC structured | `parse_normalized_candidate` (RU override, articles) |

Business rules preserved:

- Default extract types: noun / adjective / verb_form / verb_infinitive (idioms filtered out unless requested)
- User must still approve candidates before they become dictionary items
- n8n import continues to call `normalize_dictionary_row` through the same protocol

## Code

- `openai_training_extractor.py` — legacy SDK vs `ainvoke_structured`
- `ollama_training_extractor.py` — legacy `ollama_chat_json` vs `ainvoke_structured`
- Prompts via `lc.prompt_loader`

## Tests

`tests/test_lc_training_stage4.py` — mocked extract/normalize + type filter.
