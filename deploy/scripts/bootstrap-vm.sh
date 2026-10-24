#!/usr/bin/env bash
# Bootstrap Decime on VM (Cloudflare Tunnel + OpenAI text).
# Speech: either in-VM local-ai (default) or Tailscale edge when EDGE_SPEECH_HOST is set.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$DEPLOY_DIR"

if [[ ! -f .env ]]; then
  echo "Missing deploy/.env — copy .env.production.example and fill secrets."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

COMPOSE=(
  docker compose
  -f docker-compose.yml
  -f docker-compose.shared-vm.yml
  -f docker-compose.cloudflare-tunnel.yml
)

EDGE_MODE=0
if [[ -n "${EDGE_SPEECH_HOST:-}" ]]; then
  EDGE_MODE=1
  COMPOSE+=(-f docker-compose.local-ai.edge.yml)
  echo "==> EDGE_SPEECH_HOST=${EDGE_SPEECH_HOST} — Tailscale edge speech (no VM ollama/orpheus)"
else
  COMPOSE+=(-f docker-compose.local-ai.yml -f docker-compose.local-ai.eco.yml)
  echo "==> In-VM local AI (ollama + orpheus + faster-whisper)"
fi

COMPOSE+=(-f docker-compose.n8n-net.yml)

docker network inspect decime_n8n >/dev/null 2>&1 || {
  echo "ERROR: Docker network decime_n8n does not exist"
  exit 1
}

for var in AUTH_JWT_SECRET AUTH_BOOTSTRAP_ADMIN_PASSWORD; do
  if [[ -z "${!var:-}" ]]; then
    echo "Set $var in deploy/.env"
    exit 1
  fi
done

if [[ "${LLM_PROVIDER:-openai}" == "openai" ]] && [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
  exit 1
fi

if [[ "$EDGE_MODE" -eq 1 ]]; then
  echo "==> Building and starting Decime (postgres, api, web, caddy)…"
  "${COMPOSE[@]}" up -d --build postgres api web caddy
else
  echo "==> Building and starting Decime (postgres, ollama, orpheus, api, web, caddy)…"
  "${COMPOSE[@]}" up -d --build postgres ollama orpheus api web caddy

  echo "==> Pulling Ollama models (first run may take several minutes)…"
  chmod +x scripts/pull-ollama-models.sh
  ./scripts/pull-ollama-models.sh
fi

if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
  echo ""
  echo "CLOUDFLARE_TUNNEL_TOKEN is empty — add token to deploy/.env then:"
  echo "  ${COMPOSE[*]} --profile tunnel up -d cloudflared"
else
  echo "==> Starting cloudflared…"
  "${COMPOSE[@]}" --profile tunnel up -d cloudflared
fi

echo "==> Status"
"${COMPOSE[@]}" ps

echo ""
echo "Verify:"
echo "  curl -s https://api.decime.online/health"
if [[ "$EDGE_MODE" -eq 1 ]]; then
  echo "  expect: llm_provider=openai, stt_provider=openai, tts_provider=orpheus"
  echo "  edge:   curl http://${EDGE_SPEECH_HOST}:8090/health"
else
  echo "  expect: llm_provider=openai, stt_provider=faster_whisper, tts_provider=orpheus"
fi
