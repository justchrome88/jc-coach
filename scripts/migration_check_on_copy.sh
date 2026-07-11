#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DB="${SOURCE_DB:-$ROOT_DIR/data/cs2_coach.db}"
TARGET_DB="${TARGET_DB:-$(mktemp /tmp/jc-coach-migration-check.XXXXXX.db)}"
SCHEMA_BASELINE="${SCHEMA_BASELINE:-$ROOT_DIR/app/contracts/db/current_schema_baseline.json}"
PYTHON_BIN="${PYTHON:-python3}"

source_abs="$(realpath -m "$SOURCE_DB")"
target_abs="$(realpath -m "$TARGET_DB")"
production_db_abs="$(realpath -m "$ROOT_DIR/data/cs2_coach.db")"
schema_baseline_abs="$(realpath -m "$SCHEMA_BASELINE")"

if [[ ! -f "$source_abs" ]]; then
  echo "MIGRATION_COPY_CHECK_ERROR=missing_source_db:$source_abs" >&2
  exit 2
fi

if [[ ! -f "$schema_baseline_abs" ]]; then
  echo "MIGRATION_COPY_CHECK_ERROR=missing_schema_baseline:$schema_baseline_abs" >&2
  exit 5
fi

if [[ "$source_abs" == "$target_abs" ]]; then
  echo "MIGRATION_COPY_CHECK_ERROR=target_must_not_equal_source" >&2
  exit 3
fi

if [[ "$target_abs" == "$production_db_abs" ]]; then
  echo "MIGRATION_COPY_CHECK_ERROR=target_must_not_be_production_db" >&2
  exit 6
fi

if [[ -e "$target_abs" ]]; then
  source_inode="$(stat -c '%d:%i' "$source_abs")"
  target_inode="$(stat -c '%d:%i' "$target_abs")"
  if [[ "$source_inode" == "$target_inode" ]]; then
    echo "MIGRATION_COPY_CHECK_ERROR=target_must_not_equal_source" >&2
    exit 3
  fi

  if [[ -e "$production_db_abs" ]]; then
    production_inode="$(stat -c '%d:%i' "$production_db_abs")"
    if [[ "$target_inode" == "$production_inode" ]]; then
      echo "MIGRATION_COPY_CHECK_ERROR=target_must_not_be_production_db" >&2
      exit 6
    fi
  fi
fi

source_sha_before="$("$PYTHON_BIN" - "$source_abs" <<'PY'
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"

mkdir -p "$(dirname "$target_abs")"
cp "$source_abs" "$target_abs"

APP_ENV=test DATABASE_URL="sqlite:///$target_abs" "$PYTHON_BIN" <<'PY'
from __future__ import annotations

import sqlite3

from app.db.session import init_db, settings

init_db()

db_path = settings.database_url.removeprefix("sqlite:///")
connection = sqlite3.connect(db_path)
try:
    integrity = connection.execute("PRAGMA integrity_check;").fetchone()[0]
finally:
    connection.close()

if integrity != "ok":
    raise SystemExit(f"copy integrity failed: {integrity}")
PY

source_sha_after="$("$PYTHON_BIN" - "$source_abs" <<'PY'
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"

if [[ "$source_sha_before" != "$source_sha_after" ]]; then
  echo "MIGRATION_COPY_CHECK_ERROR=source_db_sha_changed" >&2
  exit 4
fi

echo "MIGRATION_COPY_CHECK_SOURCE=$source_abs"
echo "MIGRATION_COPY_CHECK_TARGET=$target_abs"
echo "MIGRATION_COPY_CHECK_SOURCE_SHA256=$source_sha_after"
echo "MIGRATION_COPY_CHECK_SOURCE_UNCHANGED=true"
echo "MIGRATION_COPY_CHECK_SCHEMA_BASELINE=$schema_baseline_abs"
"$PYTHON_BIN" "$ROOT_DIR/scripts/schema_baseline_gate.py" check \
  --db-path "$target_abs" \
  --baseline "$schema_baseline_abs"
echo "MIGRATION_COPY_CHECK_RESULT=ok"
