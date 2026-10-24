# Decime edge speech (Tailscale): models on your PC, API on the VM

## Why

A small shared VM is often too slow for Orpheus TTS (multi-minute phrases; reverse
proxies may cut long requests). Run **Whisper + Orpheus/Ollama on your PC** and
point the VM API at them over **Tailscale** (private mesh — better than a public
home tunnel).

```text
Browser  →  api.decime.online (VM API + Postgres + Caddy)
                │
                ├─ STT → http://100.x.x.x:8090/v1   (Whisper on PC)
                └─ TTS → http://100.x.x.x:5005      (Orpheus on PC)
                              └─ Ollama :11434 on PC
```

Text translate/compose stays on **OpenAI** on the VM. No ollama/orpheus containers on the VM.

---

## 1. Tailscale

1. Install [Tailscale](https://tailscale.com/download) on the **VM** and your **PC**.
2. Log in to the same tailnet on both.
3. On the PC, note the Tailscale IPv4: `tailscale ip -4` (placeholder below: `100.64.0.10`).
4. From the VM, check reachability once PC services are up (replace with your Tailscale IP):

```bash
ping -c 2 100.64.0.10
curl -sS http://100.64.0.10:8090/health
curl -sS -o /dev/null -w "%{http_code}\n" http://100.64.0.10:5005/docs
curl -sS http://100.64.0.10:11434/api/tags
```

Disable PC sleep while serving beta, or TTS/STT will fail when the laptop sleeps.

---

## 2. On the PC — start everything

Prerequisites:

- [Ollama](https://ollama.com/download) installed
- Orpheus-FastAPI cloned (see [orpheus_tts_setup.md](orpheus_tts_setup.md)); set `ORPHEUS_DIR` to that clone path
- Python 3.11+ (`py -3.11`)

One command from the repo root (waits until Whisper + Orpheus + Ollama are ready):

```powershell
.\scripts\edge\up.ps1
```

```bash
./scripts/edge/up.sh
```

Stop everything (Whisper, Orpheus, **and Ollama**):

```powershell
.\scripts\edge\down.ps1
```

```bash
./scripts/edge/down.sh
```

`up` starts Ollama if needed, launches Orpheus (:5005) and Whisper (:8090), waits for health,
then warms the Orpheus model (`keep_alive=-1`). Logs: `scripts/edge/.run/logs/`.

Or start pieces individually:

```powershell
.\scripts\edge\start-whisper.ps1          # :8090, device=auto (CUDA if available)
.\scripts\edge\start-orpheus.ps1          # :5005 → local Ollama
```

Ollama must listen for Tailscale peers:

```powershell
# PowerShell (user env) — then restart the Ollama app
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0", "User")
ollama pull sematre/orpheus:it_es
```

`start-orpheus.ps1` / `start-all.ps1` force `ORPHEUS_HOST=0.0.0.0` and
`ORPHEUS_OLLAMA_RAW=true` in Orpheus `.env` (Orpheus uses `load_dotenv(override=True)`).

**Important:** Ollama’s OpenAI `/v1/completions` path often returns *chat text* for
Orpheus instead of `<custom_token_*>` audio IDs → empty 44-byte WAV. The
Orpheus-FastAPI patch uses Ollama `/api/generate` with `raw=true` when
`ORPHEUS_OLLAMA_RAW=true` (or when the API URL contains `:11434`).

On a 6 GB GPU keep Whisper on CPU (`start-whisper.ps1 -Device cpu`) so Orpheus
has VRAM.

### Windows Firewall / sleep checklist

| Item | Action |
|------|--------|
| TCP 8090 | Allow inbound (Private / Tailscale) — Whisper |
| TCP 5005 | Allow inbound — Orpheus |
| TCP 11434 | Allow inbound — Ollama (Admin warm) |
| Sleep | Disable sleep while serving, or TTS/STT dies mid-request |

---

## 3. On the VM — edge compose (standalone)

Do **not** include `docker-compose.local-ai.yml` or `eco.yml` — speech is only on the PC.

In `deploy/.env`:

```env
EDGE_SPEECH_HOST=100.64.0.10
LLM_PROVIDER=openai
```

Bring the stack up with the edge overlay:

```bash
cd ~/decime/deploy
docker compose \
  -f docker-compose.yml \
  -f docker-compose.shared-vm.yml \
  -f docker-compose.cloudflare-tunnel.yml \
  -f docker-compose.local-ai.edge.yml \
  --profile tunnel up -d --build api
```

Or: `EDGE_SPEECH_HOST=… ./scripts/bootstrap-vm.sh`

This sets:

| Env | Value |
|-----|--------|
| `STT_PROVIDER` | `openai` + `OPENAI_STT_BASE_URL=http://$EDGE:8090/v1` |
| `TTS_PROVIDER` | `orpheus` + `ORPHEUS_TTS_BASE_URL=http://$EDGE:5005` |
| `OLLAMA_BASE_URL` | `http://$EDGE:11434` (warm from admin) |
| `AI_DOCKER_CONTROL_ENABLED` | `false` |

---

## 4. Admin AI power

Open https://decime.online/app/admin/ai/

- **Edge mode:** Power on = probe + warm remote services (does not Docker-start on VM).
- Power off = API refuses STT/TTS; PC processes keep running (stop them on the PC if you want).

---

## 5. Smoke test

1. PC: `start-all.ps1`; Tailscale connected.
2. VM: `curl http://$EDGE:8090/health` and Orpheus `/docs`.
3. Web: Mic (STT) and Play audio (TTS). First Orpheus warm can still take a minute on CPU/GPU.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `Edge Orpheus not reachable` | Tailscale IP, Orpheus bound to `0.0.0.0`, firewall 5005 |
| `Edge Whisper STT not reachable` | Whisper server up, firewall 8090 |
| STT uses OpenAI cloud by mistake | Ensure `OPENAI_STT_BASE_URL` is set (edge overlay) |
| Slow TTS | GPU drivers / smaller text; async Play still polls up to 5 min |
| Accidental VM ollama pull | Do not pass `local-ai.yml` when edged |
