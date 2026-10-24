# Decime UY — VM deploy (decime.online)

Security requirements: [docs/security_brief.md](../docs/security_brief.md)

## DNS

```text
decime.online      → VM IP   (frontend)
www.decime.online  → VM IP   (frontend)
api.decime.online  → VM IP   (FastAPI via Caddy)
```

## Architecture (public)

```text
Internet :443/:80
    ↓ Caddy (TLS, security headers)
    ├── decime.online, www.decime.online → static Next.js
    └── api.decime.online → FastAPI (internal :8000, not published)
```

**Not exposed publicly:** Postgres 5432, Ollama 11434, Orpheus 5005, n8n 5678, API :8000.

## P0 checklist (before go-live)

- [ ] DNS A records point to VM
- [ ] GCP firewall: **only** tcp:80, tcp:443 ingress
- [ ] `deploy/.env`: `APP_ENV=production`, `AUTH_ENABLED=true`
- [ ] `AUTH_JWT_SECRET` ≥ 32 chars, not a placeholder
- [ ] `AUTH_ALLOW_REGISTRATION=false`
- [ ] `PUBLIC_WEB_URL=https://decime.online`, `PUBLIC_API_URL=https://api.decime.online`
- [ ] `docker compose up -d --build` (Caddy obtains Let's Encrypt certs)
- [ ] `curl https://api.decime.online/health` → `auth_enabled: true`
- [ ] SSH: key-only login, no password auth if possible

## Quick start

```bash
cd deploy
cp .env.production.example .env
# Edit secrets — API refuses to start if production security checks fail

docker compose up -d --build
```

## Environment

```env
APP_ENV=production
AUTH_ENABLED=true
AUTH_JWT_SECRET=<openssl rand -base64 48>
AUTH_ALLOW_REGISTRATION=false
PUBLIC_WEB_URL=https://decime.online
PUBLIC_API_URL=https://api.decime.online
```

## Android APK

Production APK bakes `https://api.decime.online` (no `/api` suffix). Dev/LAN builds: set or scan the API URL in **Diagnostics** (Settings is language/logout only).

## Backups (P1)

```bash
cd ~/decime/deploy
chmod +x scripts/backup.sh scripts/install-backup-cron.sh
./scripts/backup.sh
./scripts/backup.sh --verify-latest   # read-only restore smoke
./scripts/install-backup-cron.sh      # daily 03:15 UTC
```

Writes `deploy/backups/decime-db-*.sql.gz` + `decime-audio-*.tar.gz`, keeps 14 days (`BACKUP_KEEP_DAYS`).

## HTTP-only (dev on VM, not for phones)

```bash
docker compose --profile http up -d --build
```

No auto-TLS — do not use for public beta.

## GCP firewall

```bash
# Allow web only (adjust network/tag as needed)
gcloud compute firewall-rules create decime-web \
  --allow=tcp:80,tcp:443 \
  --target-tags=decime \
  --description="Decime UY public web"
```

Do **not** create rules for 5432, 8000, 11434, 5005, 5678.

## SSH hardening (P1)

```bash
# /etc/ssh/sshd_config
PasswordAuthentication no
PermitRootLogin prohibit-password
```

## n8n + dictionary Google Sheets

n8n is not bundled in compose. On the shared VM, n8n already uses external Docker network `decime_n8n`. Shared-VM wrappers (`./dc.sh`, `scripts/bootstrap-vm.sh`) always include overlay `docker-compose.n8n-net.yml` so the API stays on that network after every redeploy (alias `decime-api`).

**Prerequisite:** network must exist before deploy (wrappers exit with an error if missing):

```bash
docker network inspect decime_n8n >/dev/null
```

```bash
cd deploy
# set N8N_* and GOOGLE_DICTIONARY_SPREADSHEET_ID in .env (see .env.production.example)
./dc.sh --profile tunnel up -d --build
```

- API alias on that network: `decime-api` → n8n calls `http://decime-api:8000` (e.g. `/health`, `/api/v1/...`)
- Webhooks from API → `http://n8n:5678/webhook/...`
- Never publish Postgres or `N8N_AUTOMATION_KEY` to the browser
- Build export/import workflows manually; contract: [docs/n8n_workflows.md](../docs/n8n_workflows.md)
- Do **not** merge `decime_n8n` into base `docker-compose.yml` — keep the optional overlay

Protect n8n UI (Basic Auth + HTTPS); never expose :5678 publicly.

## Verify

```bash
curl -s https://api.decime.online/health | jq .
curl -sI https://decime.online | grep -i strict-transport
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| API container exits on start | Check logs — JWT secret, `AUTH_ENABLED`, https URLs |
| CORS error in browser | `FRONTEND_BASE_URL=https://decime.online`, rebuild api |
| Certificate failed | DNS propagated? Ports 80/443 open? |
| 401 on API | Login; production always requires auth |
| APK cannot connect | Use `https://api.decime.online` |

## Shared VM (other projects on the same host)

If the VM already runs other stacks (e.g. **x-ui/xray on :443**, **bemulator postgres on :5432**), use the **shared-vm overlay**. Decime gets its own Docker project (`decime_*` containers/volumes) and does **not** publish :443 or :5432 on the host.

**Problem:** Caddy cannot bind `:443` when xray uses it. Browsers and the APK expect `https://decime.online` — plain HTTP on :80 is not enough.

**Solution (pick one):**

### A — Cloudflare proxy (recommended)

1. Add `decime.online` to Cloudflare; point nameservers to Cloudflare.
2. A records: `@`, `www`, `api` → VM IP, **Proxy ON** (orange cloud).
3. SSL/TLS → **Flexible** (Cloudflare HTTPS → origin HTTP :80) or **Full** if you add an origin cert later.
4. Deploy:

```bash
cd deploy
cp .env.production.example .env
# OPENAI_API_KEY, AUTH_JWT_SECRET, admin password, etc.

docker compose -f docker-compose.yml -f docker-compose.shared-vm.yml up -d --build
```

5. Verify: `https://decime.online/login/` and `https://api.decime.online/health`.

**Does not touch:** bemulator containers, x-ui/xray, slipstream, host postgres :5432.

### B — Cloudflare Tunnel (no public :80 either)

1. Create a tunnel in Cloudflare dashboard; copy `TUNNEL_TOKEN`.
2. Route hostnames to `http://caddy:80` (same compose network).
3. Add to `deploy/.env`: `CLOUDFLARE_TUNNEL_TOKEN=...`
4. Deploy:

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.shared-vm.yml \
  -f docker-compose.cloudflare-tunnel.yml up -d --build
```

### What stays isolated

| Resource | bemulator / VPN | Decime |
|----------|-----------------|--------|
| Host :443 | xray | not used |
| Host :5432 | bemulator-postgres | not used (Postgres internal only) |
| Host :6379 | bemulator-redis | not used |
| Host :80 | free | Caddy (mode A only) |
| Docker network | `bemulator_default` | `decime_default` |
| Volumes | `bemulator_*` | `decime_*` |

### Full AI on VM (~25 GiB RAM / 2 vCPU)

Default hybrid stack uses `docker-compose.local-ai.yml` **plus**
`docker-compose.local-ai.eco.yml`:

| Task | Provider | VM notes |
|------|----------|----------|
| Translate, compose, training | **OpenAI** | unchanged |
| STT | **faster-whisper `base`** | 2 CPU threads, ~4 GiB for API |
| TTS | **Orpheus** + Ollama | Orpheus kept loaded (`OLLAMA_KEEP_ALIVE=-1`), ~12 GiB for Ollama |

```bash
# Prefer: ./dc.sh --profile tunnel up -d --build
docker compose -f docker-compose.yml \
  -f docker-compose.shared-vm.yml \
  -f docker-compose.cloudflare-tunnel.yml \
  -f docker-compose.local-ai.yml \
  -f docker-compose.local-ai.eco.yml \
  -f docker-compose.n8n-net.yml \
  --profile tunnel up -d --build
```

To shrink STT footprint: `WHISPER_MODEL_SIZE=tiny` in `deploy/.env`.

### Admin AI power (STT / TTS)

Web admins can open **AI power** (`/app/admin/ai/`):

| Toggle | On | Off |
|--------|----|-----|
| STT | Load Whisper into API RAM **or** probe edge Whisper | Unload / refuse `/audio/transcribe` |
| TTS (VM) | `docker start` ollama+orpheus, then warm | `docker stop` |
| TTS (edge) | Probe/warm Orpheus on Tailscale PC | Refuse synthesize (PC stays up) |

VM Docker control needs `AI_DOCKER_CONTROL_ENABLED=true` and docker.sock.
For a home PC over Tailscale, use **edge** mode instead (below).

### Edge speech (recommended for usable Orpheus)

Run Whisper + Orpheus on your PC; VM API calls them via Tailscale.
**Do not** stack `local-ai.yml` / `eco.yml` — no VM ollama/orpheus.
See **[docs/edge_speech_tailscale.md](../docs/edge_speech_tailscale.md)**.

```bash
# deploy/.env
EDGE_SPEECH_HOST=100.64.x.x

# Prefer: ./dc.sh --profile tunnel up -d --build
docker compose -f docker-compose.yml \
  -f docker-compose.shared-vm.yml \
  -f docker-compose.cloudflare-tunnel.yml \
  -f docker-compose.local-ai.edge.yml \
  -f docker-compose.n8n-net.yml \
  --profile tunnel up -d --build
```

On the PC: `.\scripts\edge\start-all.ps1`

Text LLM is always OpenAI (`LLM_PROVIDER=openai`). Ollama on the edge PC is only for Orpheus TTS (`sematre/orpheus:it_es`), not for translate/understand.
