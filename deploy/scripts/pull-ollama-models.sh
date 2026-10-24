#!/usr/bin/env bash
# Pull Ollama models needed for Orpheus TTS only (no text LLM models).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$DEPLOY_DIR"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.shared-vm.yml -f docker-compose.cloudflare-tunnel.yml -f docker-compose.local-ai.yml)

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

TTS_MODEL="${ORPHEUS_OLLAMA_MODEL:-sematre/orpheus:it_es}"

echo "==> Waiting for Ollama..."
for _ in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T ollama ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> Pulling ${TTS_MODEL} (Orpheus TTS backend only — text uses OpenAI)..."
"${COMPOSE[@]}" exec -T ollama ollama pull "${TTS_MODEL}"

echo "==> Done. Models:"
"${COMPOSE[@]}" exec -T ollama ollama list
