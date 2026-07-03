#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${DB_PATH:-$ROOT_DIR/data/cs2_coach.db}"
PYTHON_BIN="${PYTHON:-python3}"

if [[ ! -f "$DB_PATH" ]]; then
  echo "MIGRATION_STATUS_ERROR=missing_db:$DB_PATH" >&2
  exit 2
fi

"$PYTHON_BIN" - "$DB_PATH" <<'PY'
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

db_path = Path(sys.argv[1]).resolve()
uri = f"file:{db_path}?mode=ro"

with db_path.open("rb") as handle:
    digest = hashlib.sha256(handle.read()).hexdigest()

connection = sqlite3.connect(uri, uri=True)
try:
    integrity = connection.execute("PRAGMA integrity_check;").fetchone()[0]
    user_version = connection.execute("PRAGMA user_version;").fetchone()[0]
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        ).fetchall()
    ]
finally:
    connection.close()

print(f"MIGRATION_STATUS_DB={db_path}")
print(f"MIGRATION_STATUS_SHA256={digest}")
print(f"MIGRATION_STATUS_INTEGRITY={integrity}")
print(f"MIGRATION_STATUS_USER_VERSION={user_version}")
print(f"MIGRATION_STATUS_TABLES={','.join(tables)}")
PY
