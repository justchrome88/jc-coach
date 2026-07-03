#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCTION_DB="$ROOT_DIR/data/cs2_coach.db"
DB_BACKUP=""
ARTIFACTS_BACKUP=""
TARGET_DB=""
TARGET_ROOT="$ROOT_DIR"
VERIFY_ONLY=0

usage() {
  cat <<'USAGE'
Usage:
  scripts/restore_runtime.sh --db-backup backups/cs2_coach_YYYYMMDD_HHMMSS.db --target-db /tmp/jc-coach-restore-test.db --verify-only
  scripts/restore_runtime.sh --db-backup backups/cs2_coach_YYYYMMDD_HHMMSS.db --target-db data/cs2_coach.db

Options:
  --db-backup PATH        SQLite backup file to restore from.
  --artifacts-backup PATH Optional runtime artifacts tar.gz.
  --target-db PATH        Target SQLite DB path. Production target requires ALLOW_PRODUCTION_RESTORE=1.
  --target-root PATH      Target root for artifacts restore. Repo root requires ALLOW_PRODUCTION_RESTORE=1.
  --verify-only           Verify restored DB copy and never restore artifacts.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-backup)
      DB_BACKUP="$2"
      shift 2
      ;;
    --artifacts-backup)
      ARTIFACTS_BACKUP="$2"
      shift 2
      ;;
    --target-db)
      TARGET_DB="$2"
      shift 2
      ;;
    --target-root)
      TARGET_ROOT="$2"
      shift 2
      ;;
    --verify-only)
      VERIFY_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$DB_BACKUP" || -z "$TARGET_DB" ]]; then
  usage >&2
  exit 2
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "python3 or python is required to resolve restore paths safely." >&2
  exit 1
fi

if [[ ! -f "$DB_BACKUP" ]]; then
  echo "DB backup was not found: $DB_BACKUP" >&2
  exit 1
fi

TARGET_DB_ABS="$("$PYTHON_BIN" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$TARGET_DB")"
PRODUCTION_DB_ABS="$("$PYTHON_BIN" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$PRODUCTION_DB")"
TARGET_ROOT_ABS="$("$PYTHON_BIN" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$TARGET_ROOT")"
ROOT_DIR_ABS="$("$PYTHON_BIN" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$ROOT_DIR")"

if [[ "$TARGET_DB_ABS" == "$PRODUCTION_DB_ABS" && "${ALLOW_PRODUCTION_RESTORE:-0}" != "1" ]]; then
  echo "Refusing to restore over production DB without ALLOW_PRODUCTION_RESTORE=1." >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET_DB_ABS")"
cp "$DB_BACKUP" "$TARGET_DB_ABS"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$TARGET_DB_ABS" "PRAGMA integrity_check;" | grep -qx "ok"
fi

if [[ "$VERIFY_ONLY" == "1" ]]; then
  echo "RESTORE_VERIFY_OK=$TARGET_DB_ABS"
  exit 0
fi

if [[ -n "$ARTIFACTS_BACKUP" ]]; then
  if [[ ! -f "$ARTIFACTS_BACKUP" ]]; then
    echo "Artifacts backup was not found: $ARTIFACTS_BACKUP" >&2
    exit 1
  fi
  if [[ "$TARGET_ROOT_ABS" == "$ROOT_DIR_ABS" && "${ALLOW_PRODUCTION_RESTORE:-0}" != "1" ]]; then
    echo "Refusing to restore artifacts into repo root without ALLOW_PRODUCTION_RESTORE=1." >&2
    exit 1
  fi
  mkdir -p "$TARGET_ROOT_ABS"
  tar -xzf "$ARTIFACTS_BACKUP" -C "$TARGET_ROOT_ABS"
fi

echo "RESTORE_OK=$TARGET_DB_ABS"
