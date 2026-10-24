#!/usr/bin/env bash
# Install daily cron for Decime backups on the VM.
# Usage: ./scripts/install-backup-cron.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_SH="$SCRIPT_DIR/backup.sh"
LOG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/backups"
mkdir -p "$LOG_DIR"
chmod +x "$BACKUP_SH"

CRON_LINE="15 3 * * * $BACKUP_SH >> $LOG_DIR/backup.log 2>&1"

# Replace any previous Decime backup cron lines, keep the rest.
EXISTING="$(crontab -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "$EXISTING" | grep -v 'deploy/scripts/backup.sh' || true)"
{
  printf '%s\n' "$FILTERED"
  printf '%s\n' "$CRON_LINE"
} | sed '/^$/d' | crontab -

echo "==> Installed cron:"
crontab -l | grep backup.sh
echo "Logs: $LOG_DIR/backup.log"
