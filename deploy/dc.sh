#!/usr/bin/env bash
# Canonical Decime compose wrapper — always stacks shared-vm + tunnel + speech + n8n-net.
# Speech: EDGE_SPEECH_HOST set → local-ai.edge.yml; otherwise in-VM local-ai (+ eco).
# n8n: docker-compose.n8n-net.yml (external network decime_n8n must already exist).
#
# Usage (from deploy/):
#   ./dc.sh ps
#   ./dc.sh --profile tunnel up -d cloudflared
#   ./dc.sh -f docker-compose.local-ai.edge.yml up -d api   # still fine; edge auto-added if host set
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

docker network inspect decime_n8n >/dev/null 2>&1 || {
  echo "ERROR: Docker network decime_n8n does not exist"
  exit 1
}

ARGS=(
  docker compose
  -f docker-compose.yml
  -f docker-compose.shared-vm.yml
  -f docker-compose.cloudflare-tunnel.yml
)

if [[ -n "${EDGE_SPEECH_HOST:-}" ]]; then
  ARGS+=(-f docker-compose.local-ai.edge.yml)
else
  ARGS+=(-f docker-compose.local-ai.yml -f docker-compose.local-ai.eco.yml)
fi

ARGS+=(-f docker-compose.n8n-net.yml)

exec "${ARGS[@]}" "$@"
