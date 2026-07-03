#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${DB_PATH:-$ROOT_DIR/data/cs2_coach.db}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
TIMESTAMP="${BACKUP_TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$BACKUP_DIR"

DB_BACKUP="$BACKUP_DIR/cs2_coach_${TIMESTAMP}.db"
ARTIFACTS_BACKUP="$BACKUP_DIR/runtime_artifacts_${TIMESTAMP}.tar.gz"
MANIFEST="$BACKUP_DIR/backup_${TIMESTAMP}.manifest.txt"

if [[ ! -f "$DB_PATH" ]]; then
  echo "Database was not found: $DB_PATH" >&2
  exit 1
fi

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_PATH" ".backup '$DB_BACKUP'"
  sqlite3 "$DB_BACKUP" "PRAGMA integrity_check;" | grep -qx "ok"
else
  cp "$DB_PATH" "$DB_BACKUP"
fi

tar -czf "$ARTIFACTS_BACKUP" \
  --exclude="*.dem" \
  --exclude="*.dem.bz2" \
  --exclude="data/steam_bot_credentials" \
  --exclude="data/steam_bot_credentials/*" \
  -C "$ROOT_DIR" \
  data/reports data/uploads data/incoming_demos data/ai_handoffs \
  2>/dev/null || true

{
  echo "created_at=$TIMESTAMP"
  echo "root_dir=$ROOT_DIR"
  echo "db_source=$DB_PATH"
  echo "db_backup=$DB_BACKUP"
  echo "artifacts_backup=$ARTIFACTS_BACKUP"
  echo "excluded=.env,data/steam_bot_credentials,*.dem,*.dem.bz2"
  echo "restore_check=scripts/restore_runtime.sh --db-backup '$DB_BACKUP' --target-db /tmp/jc-coach-restore-test.db --verify-only"
} > "$MANIFEST"

echo "DB_BACKUP=$DB_BACKUP"
echo "ARTIFACTS_BACKUP=$ARTIFACTS_BACKUP"
echo "MANIFEST=$MANIFEST"
