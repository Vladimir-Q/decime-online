#!/usr/bin/env bash
# Backup Postgres + audio volume for Decime UY (run on VM via cron)
# Usage: ./scripts/backup.sh [output_dir]
#
# Restore smoke (non-destructive):
#   ./scripts/backup.sh --verify-latest
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="${1:-$DEPLOY_DIR/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"

# Match production stack (project name decime + overlays).
COMPOSE=(
  docker compose
  --project-name decime
  -f "$DEPLOY_DIR/docker-compose.yml"
  -f "$DEPLOY_DIR/docker-compose.shared-vm.yml"
  -f "$DEPLOY_DIR/docker-compose.cloudflare-tunnel.yml"
  -f "$DEPLOY_DIR/docker-compose.local-ai.yml"
  -f "$DEPLOY_DIR/docker-compose.local-ai.eco.yml"
)

cd "$DEPLOY_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PG_USER="${POSTGRES_USER:-decime}"
PG_DB="${POSTGRES_DB:-decime}"

verify_latest() {
  local latest_db
  latest_db="$(ls -1t "$OUT_DIR"/decime-db-*.sql.gz 2>/dev/null | head -1 || true)"
  if [[ -z "$latest_db" ]]; then
    echo "No database backups found in $OUT_DIR" >&2
    exit 1
  fi

  echo "==> Verify dump readable: $latest_db"
  gzip -t "$latest_db"
  local tables
  tables="$(gzip -dc "$latest_db" | grep -c '^CREATE TABLE' || true)"
  echo "    CREATE TABLE statements: $tables"
  if [[ "${tables:-0}" -lt 1 ]]; then
    echo "Dump looks empty (no CREATE TABLE)" >&2
    exit 1
  fi

  local latest_audio
  latest_audio="$(ls -1t "$OUT_DIR"/decime-audio-*.tar.gz 2>/dev/null | head -1 || true)"
  if [[ -n "$latest_audio" ]]; then
    echo "==> Verify audio archive: $latest_audio"
    tar -tzf "$latest_audio" >/dev/null
    echo "    entries: $(tar -tzf "$latest_audio" | wc -l)"
  else
    echo "==> No audio archive yet (ok if no files uploaded)"
  fi

  echo "==> Restore smoke OK (read-only checks; live DB untouched)"
}

if [[ "${1:-}" == "--verify-latest" ]]; then
  OUT_DIR="${2:-$DEPLOY_DIR/backups}"
  verify_latest
  exit 0
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

echo "==> Postgres dump"
"${COMPOSE[@]}" exec -T postgres pg_dump -U "$PG_USER" "$PG_DB" \
  | gzip > "$OUT_DIR/decime-db-$STAMP.sql.gz"
gzip -t "$OUT_DIR/decime-db-$STAMP.sql.gz"

echo "==> Audio files (api volume)"
"${COMPOSE[@]}" run --rm --no-deps \
  -v "$OUT_DIR:/backup" \
  api sh -c 'tar -czf /backup/decime-audio-'"$STAMP"'.tar.gz -C /app data/audio 2>/dev/null || tar -czf /backup/decime-audio-'"$STAMP"'.tar.gz --files-from /dev/null'

echo "==> Retention: delete backups older than ${KEEP_DAYS} days"
find "$OUT_DIR" -maxdepth 1 -type f \( -name 'decime-db-*.sql.gz' -o -name 'decime-audio-*.tar.gz' \) -mtime +"$KEEP_DAYS" -print -delete || true

echo "==> Done: $OUT_DIR"
ls -lh "$OUT_DIR"/*"$STAMP"* 2>/dev/null || true
