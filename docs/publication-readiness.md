# Decime UY — Repository publication readiness

**Date:** 2026-10-24  
**Baseline tree source:** private repo commit `32e94a6603d3` + publication-readiness scrub  
**History:** **clean** (single root commit in this publication copy — no prior private history)

Safe public summary only. Detailed secret values and private audit artifacts stay on the maintainer machine outside any public remote.

This document describes whether the **MVP source tree** is safe to share publicly and what the maintainer must confirm before pushing or changing GitHub visibility.

---

## Inventory (current tree)

| Area | Classification | Notes |
|------|----------------|-------|
| `apps/api`, `apps/web` source | **Public** | Core product |
| `apps/api/evals/datasets`, `evals/reports/pilot-2026-10` | **Public** | Synthetic/pilot cases; no emails found in datasets |
| `docs/` architecture, contracts, evals, case study | **Public** | Keep |
| `deploy/*.example`, `deploy/README.md` | **Public** | Placeholders only |
| `.env.example`, `deploy/.env.production.example` | **Public** | Templates |
| `.github/workflows/` | **Public** | Free CI + manual paid smoke |
| `docs/conversation_log.md` | **Sensitive / Internal** | Absent from HEAD; still in history |
| `docs/handoff_edge_speech_2026-09-29.md` | **Sensitive** | Absent from HEAD; history contains real private-mesh addresses |
| Local `.env`, `data/`, keystores, UI dumps | **Sensitive** | Gitignored; must stay untracked |
| Transient eval `dbg` / `tmp-*` reports | **Internal** | Gitignored |
| `LICENSE` | **Uncertain** | Not present — maintainer chooses |

---

## Security audit (summary)

### Working tree / HEAD

- No committed `.env`, private keys, or keystores in `git ls-files`.
- Example Tailscale addresses in docs/tests use a **placeholder** CGNAT form (`100.64.0.10`), not the addresses previously recorded in the private handoff note.
- One Gitleaks `generic-api-key` hit on an intentionally invalid E2E session token was replaced with a non JWT-shaped fixture.
- Eval pilot metrics in README / case study match JSON artifacts (Human 9/18/3; Judge SF 3/4/23; simulations 400+400).

### Git history (all reachable commits)

| Finding | Severity | Location (safe reference) |
|---------|----------|---------------------------|
| Private Tailscale addresses in deleted handoff doc | **High** | Historical blob of `docs/handoff_edge_speech_2026-09-29.md` |
| Internal agent conversation log | **Medium** | Historical blobs of `docs/conversation_log.md` |
| Gitleaks full-history scan | **Low** | Prior false positive on invalid JWT fixture (fixed in tree) |

**Gitleaks does not erase history.** Ignoring a path only affects new commits.

Status implication: **opening the current remote history as-is is blocked** until history is rewritten or a clean public copy is published.

---

## Publication copy status

**Strategy B applied locally:** this tree is the scrubbed MVP snapshot with a **new clean Git history**. It is **not** pushed to GitHub yet.

- Private development repo (`Vladimir-Q/decime`) is unchanged.
- Historical private-mesh handoff notes and conversation logs are **not** present in this copy’s objects.
- Maintainer still chooses license, remote name/visibility, and when to `git push`.

### Alternative (not used here): Strategy A

Rewrite history of the existing private remote with `git filter-repo`, then force-push. Higher coordination cost if forks/PR caches retain old objects.

---

## Changes already applied on this branch (tree only)

- README EN/RU: working `git clone` URL.
- `.gitignore`: keystores, edge scratch, transient evals, QA dumps, zip scratch.
- Docs/scripts: remove machine-specific workspace paths; Tailscale examples use placeholders.
- CI: `permissions: contents: read` on workflows.
- `SECURITY.md`, `.gitleaks.toml`, `scripts/security/scan-secrets.ps1`.
- Invalid E2E token fixture made scanner-safe.

---

## Maintainer decisions still required

1. Choose **Strategy A or B** (and approve any force-push / new remote).
2. Choose a **license** (none / MIT / Apache-2.0 — not selected automatically).
3. After history cleanup: enable GitHub secret scanning + push protection; consider Dependabot.
4. Confirm repository About / topics / website (`https://decime.online`).
5. Optionally add safe product screenshots or a short demo video (not required to share source).
6. If any real credential was ever pasted into a deleted doc or chat paste: **rotate** it (removal from Git is insufficient).

---

## Validation run (2026-10-24)

| Check | Result |
|-------|--------|
| `ruff check src` (apps/api) | PASS |
| `pytest -q` free suite | PASS — 155 passed, 5 skipped |
| `npm run typecheck` / `npm run build` | PASS |
| Internal Markdown links (README, case study, docs index) | PASS — 260 links, 0 missing |
| Fresh tree export (no local `.env` / venv) | PASS — Fake LLM `/health` ok; 155 passed; web typecheck+build ok |
| Gitleaks history (`--all`) | 1 historical hit: obsolete invalid JWT fixture in older `scripts/android_e2e_session.py` (not a live credential) |
| Local disk `.env` / `deploy/.env.vm.tmp` | Present on maintainer machine, **gitignored**, not in `git ls-files` |
| pip-audit / npm audit | Findings present (see private audit folder); no mass upgrades in this pass |

Paid LLM smoke / eval: **not run** (by design).

---

## Publication checklist

| Category | Status |
|----------|--------|
| Source code (current tree) | PASS |
| Git history | PASS (clean publication copy; private repo history unchanged) |
| Secrets in HEAD | PASS |
| Personal / private network data in HEAD | PASS |
| README EN/RU | PASS |
| Case study EN/RU | PASS |
| LLM evaluation consistency | PASS |
| CI workflows hardened | PASS |
| Local free tests | PASS |
| Fresh clone reproducibility | PASS |
| Infrastructure docs | PASS WITH LIMITATIONS |
| Dependencies | PASS WITH LIMITATIONS (advisories logged; no drive-by upgrades) |
| License | PASS (PolyForm Noncommercial 1.0.0) |
| Demo materials | PASS WITH LIMITATIONS (none committed) |
| Repository metadata | NOT VERIFIED (remote settings unchanged) |

**Overall (this clean copy):** **PUBLICATION READY — awaiting owner approval** for remote create/push and visibility. License is PolyForm Noncommercial 1.0.0. Do not push until the maintainer confirms.
