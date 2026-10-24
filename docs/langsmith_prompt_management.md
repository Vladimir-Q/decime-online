# LangSmith prompt management

Decime keeps prompt **history, diff, tags, and environment pointers** in LangSmith. The API only resolves a tag to one commit at startup, checks the template, and then reuses it. It does not implement its own registry, tags, or promotion.

The running default is still `DECIME_PROMPT_SOURCE=local`. Production behavior does not change until that setting is switched and the process is restarted. The `production` tag was not created.

## Words that matter

| Term | Meaning here |
|------|----------------|
| Prompt commit | One saved state of a prompt. The id Decime stores is the 64-character `commit_hash` returned by LangSmith. It does not move when you edit the prompt again. |
| Immutable revision | That hash. A later edit creates a new hash. Old experiments keep the old hash. |
| Environment pointer | A tag such as `staging` or `production`. It points at one commit and can be moved. It is not itself a version. |
| Semver tag | `v1-0-0` means baseline v1.0.0. LangSmith tag names cannot contain dots, so the label uses hyphens. |
| Promotion | Moving `production` to a commit that was already on `staging` after review. Decime does not do this by itself. |
| Snapshot | A JSON copy of one exact commit, shipped with the API. Used only when LangSmith is down **and** the requested hash matches the file. |
| Schema hash | SHA-256 of the JSON schema still defined in Python. The prompt and the schema are versioned separately. |
| Code revision | `git rev-parse HEAD`, or `DECIME_CODE_REVISION`, or `unknown` when git is absent. |
| Regression | Same dataset and model, two prompt commits. Not run in this change. Old scores were not recomputed. |

## Prompts

| Operation | LangSmith name | Baseline commit (`v1-0-0` and `staging`) |
|-----------|----------------|------------------------------------------|
| `translate_to_esuy` | `decime-translate-esuy` | `6ab87799258037d4719e7c11033e76605368c4039d9e7c44c27efa578fdad8b3` |
| `understand_incoming` | `decime-understand-incoming` | `b7ed1b147e6cf590033143f4d091c5a6325d7e607f4bd0df6f8a04f795a22650` |
| `extract_candidates` | `decime-extract-candidates` | `c775f38cee27e12c721b0b82a1a5958fb10b35da03074ba0c45daad47b86ab06` |
| `normalize_dictionary_row` | `decime-normalize-dictionary` | `953b8d339fc713e528d6a94dad978e6d64454d5ab2702c32cfb1f4eb9f1b5c7d` |

`locale_validate_uy.md` is not registered. No production code loads it.

`decime-translate-esuy` also has commit `8c20394340512640f136c1e0d02b1550ebf9e9d0394ca4ad2d9d7f09c9f39d43`. That commit used Jinja2. LangSmith can store it, but `pull_prompt` refuses to load Jinja2. It is not tagged and must not be used.

Judge prompts stay in Python (`judge.py`, `judge_pilot.py`). They are not production prompts. New eval metadata records `judge_prompt_version=not_versioned`. Reports already on disk are left as they are; their prompt commit is `legacy_unknown` because it was not recorded at the time.

## What is inside a prompt

Each prompt is a `ChatPromptTemplate`:

- system message: the current markdown file, unchanged
- human message: the instructions that used to be assembled in Python, plus `{{{payload_json}}}`

Mustache sections choose A2 vs default wording and the Spanish retry paragraph. The JSON payload is one variable, so `{` in user text is not a template slot. Rendered messages match the pre-migration strings byte for byte.

Output schemas stay in `llm_json_schemas.py`. Each call records `schema_sha256` next to `prompt_commit`. Structured Outputs are still `json_schema` / `strict=True`. `StructuredPrompt` was not adopted: LangChain's loader and the current `with_structured_output` path are enough, and a second schema application would be easy to get wrong.

## Environments

```text
edit in LangSmith UI
    -> new commit hash
    -> move tag staging
    -> Decime restart with DECIME_PROMPT_ENV=staging
    -> review
    -> move tag production   (owner confirms)
    -> Decime restart with DECIME_PROMPT_ENV=production
```

Changing the tag in the UI does nothing to a process that is already running. The process resolved the tag once at startup.

## Configuration

```env
DECIME_PROMPT_SOURCE=local          # local | langsmith
DECIME_PROMPT_ENV=production        # tag name, used only when source=langsmith
DECIME_PROMPT_PINS=                 # optional JSON {"decime-translate-esuy":"<64-char hash>"}
DECIME_PROMPT_SNAPSHOT_DIR=        # default: packaged prompts/snapshots
DECIME_CODE_REVISION=               # optional, for images without git
```

`local` reads the checked-in templates and does not call LangSmith. There is no commit hash in that mode. Tracing then has `prompt_source=local` and `prompt_sha256`, and omits `prompt_commit`.

`langsmith` requires `LANGSMITH_API_KEY`. At startup Decime calls `pull_prompt_commit("name:tag")` and stores `commit_hash`. Later requests reuse that template. A pin skips the tag and loads that hash. If the hub is down, a snapshot is used only when its `commit_hash` is the same. Another snapshot is an error, not a silent fallback. If the tag cannot be resolved and there is no pin, startup fails.

## Check the active version

`GET /health` includes:

- `prompt_source`
- `prompt_env`
- `prompt_commits` — `operation=<commit-or-local>:<sha256 prefix>`

LangSmith traces, when tracing is already enabled, add `prompt_id`, `prompt_environment`, `prompt_commit`, `prompt_sha256`, `schema_sha256`, `model`, `code_revision`. User text is not copied into metadata. Tracing stays off unless `LLM_TRACING_ENABLED` is set, and production tracing still needs `LLM_TRACING_ALLOW_PRODUCTION`.

## Create a commit

In the LangSmith UI: Prompts → `decime-translate-esuy` → edit the human or system text → Commit. The new row has a new hash. `v1-0-0` and `staging` stay where they were until you move them.

From the repo, the baseline push (private, no model call) is:

```bash
cd apps/api
python scripts/push_langsmith_prompts.py --tag-staging
```

`--also-tag-production` exists and was not used.

## Rollback

1. In LangSmith, open the prompt commits and copy the hash you want back.
2. Move the tag:

```bash
cd apps/api
# staging has no extra confirm
python scripts/rollback_langsmith_prompt.py decime-translate-esuy <64-char-hash> staging

# production refuses unless the owner sets this
DECIME_CONFIRM_PROMPT_PRODUCTION=1 python scripts/rollback_langsmith_prompt.py decime-translate-esuy <64-char-hash> production
```

3. Restart the API (`DECIME_PROMPT_SOURCE=langsmith`).
4. `GET /health` and confirm `prompt_commits` shows that hash.
5. Free checks: `ruff check src` and `pytest -q`.

Rollback does not edit Python, delete rows, or rewrite old prompt text. The tag moves. The old commit remains.

## Evaluation

Completed October 2026 runs were not opened or re-scored. They have no prompt commit. Treat them as `legacy_unknown`.

A future comparison is a plan only:

```bash
python scripts/eval_prompt_regression.py --commit-a <hash> --commit-b <hash>
```

It prints dataset, model, and the two hashes. It does not call a model. `DECIME_RUN_EVAL=1` does not start a paid run from this script. New eval reports from `runner.py` record the prompt identity of the process that produced them.

## Limits

- No per-request pull. A new tag is picked up on restart.
- `production` tag is not set.
- Jinja2 prompts cannot be pulled with the installed SDK.
- Snapshots are message text, rebuilt by Decime. They are not LangChain `load()` manifests.
- Schema changes are visible as a new `schema_sha256`, not as a prompt commit.
- Public Prompt Hub was not used. All four prompts are private.

## Case study — Prompt Versioning and Regression Evaluation

Decime's translation behavior lived in two places: a markdown system prompt and Python that built the human message (A2 wording, a Spanish retry, and the JSON payload). A change in either place changed the model, but neither place had a version an experiment could cite.

LangSmith Prompt Hub is now the history. Each private prompt is a chat template. A commit hash is the immutable revision. Tags `staging` and `v1-0-0` are movable pointers. Decime resolves the pointer once at startup, caches the template, and writes the hash, a SHA-256 of the template, a SHA-256 of the JSON schema, the model, and the git revision onto the trace. If the hub is unavailable, it will load a snapshot of that same hash and label the source `local_snapshot`. It will not swap in an older hash.

The baseline templates render the same system and human messages as the code they replaced. No quality claim follows from that: the messages are the same, so a comparative eval would not be measuring a prompt change. A real comparison is specified and not executed: one dataset (`ru_esuy_judge_v1`), one model (`gpt-6-luna`), two commit hashes. Historical human and judge scores stay as recorded and are marked `legacy_unknown` for prompt identity. Rollback is moving the environment tag and restarting the process, which was checked with the tag API and free tests, not with a production deploy.
