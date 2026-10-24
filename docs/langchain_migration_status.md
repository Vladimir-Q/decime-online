# LangChain migration — living status

**Last updated:** 2026-10-17  
**Current:** LangChain is the **only** product text path (`LLM_ORCHESTRATOR=langchain`). Local Ollama text LLM and the legacy SDK orchestrator are removed.

| Stage docs | Status | Notes |
|------------|--------|-------|
| `langchain_migration_stage0.md` … `stage8.md` | **Historical** | Written during the migration; may still mention optional `[langchain]`, `legacy` rollback, or Ollama text. Trust this file + [../README.md](../README.md) for current behaviour. |
| `langchain_migration_stage8.md` | Docs / runbooks wrap-up | Read with the banner at the top of that file (architecture diagram in stage8 is partly outdated). |

### Quick refs

```bash
cd apps/api
pip install -e ".[dev,local-stt]"   # langchain deps are core (not an optional extra)
pytest -q
python scripts/run_llm_eval.py --provider fake   # optional eval harness
```

- Text: `LLM_PROVIDER=openai` + optional `OPENAI_TEXT_BASE_URL` (OpenAI-compatible)
- Prompts: local templates by default. LangSmith commits, staging tag, and snapshots: [langsmith_prompt_management.md](langsmith_prompt_management.md). `DECIME_PROMPT_SOURCE` stays `local` until a restart is intentional.
- Speech: Whisper / edge STT; Orpheus TTS (Ollama hosts voice model only)
- Free CI: `.github/workflows/api-tests.yml`, `.github/workflows/web-ci.yml`
- Paid smoke (manual): `.github/workflows/api-llm-smoke.yml` (`LLM_ORCHESTRATOR=langchain` only)
