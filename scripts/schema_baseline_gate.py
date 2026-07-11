#!/usr/bin/env python3
"""Create and check deterministic SQLite schema baselines."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "cs2_coach.db"
DEFAULT_BASELINE = (
    ROOT
    / "app"
    / "contracts"
    / "db"
    / "current_schema_baseline.json"
)
BASELINE_VERSION = 1


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def normalize_sql(sql: str | None) -> str | None:
    if sql is None:
        return None
    return " ".join(sql.split())


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def compact_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def schema_hash(schema: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(compact_json(schema).encode("utf-8")).hexdigest()


def comparison_schema(schema: dict[str, Any]) -> dict[str, Any]:
    comparable = copy.deepcopy(schema)
    for table in comparable.get("tables", []):
        indexes = table.get("indexes", [])
        indexes.sort(key=lambda item: item["name"])
        for seq, index in enumerate(indexes):
            if "seq" in index:
                index["seq"] = seq
    return comparable


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    resolved = db_path.resolve()
    if not resolved.exists():
        raise SystemExit(f"SCHEMA_BASELINE_ERROR=missing_db:{resolved}")
    return sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)


def pragma_rows(connection: sqlite3.Connection, pragma_name: str, identifier: str) -> list[sqlite3.Row]:
    quoted = quote_identifier(identifier)
    return list(connection.execute(f"PRAGMA {pragma_name}({quoted});"))


def inspect_schema(db_path: Path) -> dict[str, Any]:
    connection = connect_readonly(db_path)
    connection.row_factory = sqlite3.Row
    try:
        user_version = connection.execute("PRAGMA user_version;").fetchone()[0]
        application_id = connection.execute("PRAGMA application_id;").fetchone()[0]
        objects = [
            {
                "type": row["type"],
                "name": row["name"],
                "tbl_name": row["tbl_name"],
                "sql": normalize_sql(row["sql"]),
            }
            for row in connection.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_master
                WHERE type IN ('table', 'index', 'trigger', 'view')
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY type, name
                """
            )
        ]

        table_names = [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        tables = []
        for table_name in table_names:
            columns = [
                {
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": row["notnull"],
                    "default": row["dflt_value"],
                    "pk": row["pk"],
                }
                for row in pragma_rows(connection, "table_info", table_name)
            ]
            foreign_keys = [
                {
                    "id": row["id"],
                    "seq": row["seq"],
                    "table": row["table"],
                    "from": row["from"],
                    "to": row["to"],
                    "on_update": row["on_update"],
                    "on_delete": row["on_delete"],
                    "match": row["match"],
                }
                for row in pragma_rows(connection, "foreign_key_list", table_name)
            ]
            indexes = []
            for index_row in pragma_rows(connection, "index_list", table_name):
                index_name = index_row["name"]
                if index_name.startswith("sqlite_"):
                    continue
                indexes.append(
                    {
                        "seq": index_row["seq"],
                        "name": index_name,
                        "unique": index_row["unique"],
                        "origin": index_row["origin"],
                        "partial": index_row["partial"],
                        "columns": [
                            {
                                "seqno": row["seqno"],
                                "cid": row["cid"],
                                "name": row["name"],
                                "desc": row["desc"],
                                "coll": row["coll"],
                                "key": row["key"],
                            }
                            for row in pragma_rows(connection, "index_xinfo", index_name)
                            if row["key"] == 1
                        ],
                    }
                )
            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                    "indexes": sorted(indexes, key=lambda item: item["name"]),
                }
            )
    finally:
        connection.close()

    return {
        "engine": "sqlite",
        "application_id": application_id,
        "user_version": user_version,
        "objects": objects,
        "tables": tables,
    }


def build_baseline(db_path: Path) -> dict[str, Any]:
    schema = inspect_schema(db_path)
    return {
        "schema_baseline_version": BASELINE_VERSION,
        "source_files": [
            "data/cs2_coach.db (schema only, read-only)",
            "_legacy_archive/r02a2-2026-07-11/docs/foundation_hardening/"
            "2026-07-06-readiness-recovery-plan/current_schema_baseline.json",
        ],
        "schema_hash": schema_hash(schema),
        "schema": schema,
    }


def read_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"SCHEMA_GATE_ERROR=missing_baseline:{path.resolve()}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_baseline_version") != BASELINE_VERSION:
        raise SystemExit("SCHEMA_GATE_ERROR=unsupported_baseline_version")
    if "schema" not in payload:
        raise SystemExit("SCHEMA_GATE_ERROR=missing_schema_payload")
    return payload


def write_baseline(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path)
    output_path = Path(args.output)
    baseline = build_baseline(db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(canonical_json(baseline))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output_path)
    print(f"SCHEMA_BASELINE_DB={db_path.resolve()}")
    print(f"SCHEMA_BASELINE_OUTPUT={output_path.resolve()}")
    print(f"SCHEMA_BASELINE_HASH={baseline['schema_hash']}")
    print("SCHEMA_BASELINE_RESULT=written")
    return 0


def check_baseline(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path)
    baseline_path = Path(args.baseline)
    baseline = read_baseline(baseline_path)
    current = build_baseline(db_path)
    baseline_schema = comparison_schema(baseline["schema"])
    current_schema = comparison_schema(current["schema"])
    baseline_hash = schema_hash(baseline_schema)
    current_hash = schema_hash(current_schema)

    print(f"SCHEMA_GATE_DB={db_path.resolve()}")
    print(f"SCHEMA_GATE_BASELINE={baseline_path.resolve()}")
    print(f"SCHEMA_GATE_BASELINE_HASH={baseline_hash}")
    print(f"SCHEMA_GATE_CURRENT_HASH={current_hash}")
    if baseline_schema == current_schema:
        print("SCHEMA_GATE_RESULT=match")
        return 0

    print("SCHEMA_GATE_RESULT=mismatch")
    baseline_lines = canonical_json(baseline_schema).splitlines(keepends=True)
    current_lines = canonical_json(current_schema).splitlines(keepends=True)
    diff = difflib.unified_diff(
        baseline_lines,
        current_lines,
        fromfile="baseline_schema",
        tofile="current_schema",
    )
    print("SCHEMA_GATE_DIFF_BEGIN")
    sys.stdout.writelines(diff)
    print("SCHEMA_GATE_DIFF_END")
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser("write-baseline", help="write a deterministic schema baseline")
    write_parser.add_argument("--db-path", default=str(DEFAULT_DB), help="SQLite DB to inspect read-only")
    write_parser.add_argument("--output", default=str(DEFAULT_BASELINE), help="baseline JSON output path")
    write_parser.set_defaults(func=write_baseline)

    check_parser = subparsers.add_parser("check", help="compare a SQLite DB schema to a baseline")
    check_parser.add_argument("--db-path", default=str(DEFAULT_DB), help="SQLite DB to inspect read-only")
    check_parser.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="baseline JSON path")
    check_parser.set_defaults(func=check_baseline)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
