#!/usr/bin/env python3
"""Isolated SQLite migration for append-only metric snapshot semantics.

The production database path is deliberately refused. M03 must copy/backup and
explicitly authorize production application before this guard can be changed.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_DB = (ROOT / "data/cs2_coach.db").resolve()


def upgrade(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_snapshots)")}
    if "semantic_version" in columns:
        return
    connection.executescript(
        """
        ALTER TABLE metric_snapshots RENAME TO metric_snapshots_legacy_v1;
        CREATE TABLE metric_snapshots (
            id INTEGER PRIMARY KEY,
            owner_user_id INTEGER REFERENCES users(id),
            match_id INTEGER NOT NULL REFERENCES matches(id),
            player_key VARCHAR(255) NOT NULL,
            player_name VARCHAR(255),
            player_steamid VARCHAR(32),
            source VARCHAR(80) NOT NULL,
            metric_domain VARCHAR(80) NOT NULL DEFAULT 'legacy',
            semantic_version VARCHAR(40) NOT NULL DEFAULT '1.0.0',
            scope VARCHAR(40) NOT NULL DEFAULT 'player_match',
            validation_status VARCHAR(40) NOT NULL DEFAULT 'legacy_unverified',
            implementation_version VARCHAR(120),
            input_event_hash VARCHAR(64),
            source_parser_artifact_id INTEGER REFERENCES demo_parse_artifacts(id),
            source_event_set_id VARCHAR(255),
            metrics_json TEXT NOT NULL,
            confidence_baseline_json TEXT NOT NULL,
            caveats_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT uq_metric_snapshot_semantic_identity UNIQUE (
                owner_user_id, match_id, player_key, metric_domain,
                semantic_version, source, source_event_set_id
            )
        );
        INSERT INTO metric_snapshots (
            id, owner_user_id, match_id, player_key, player_name, player_steamid,
            source, metric_domain, semantic_version, scope, validation_status,
            source_parser_artifact_id, source_event_set_id, metrics_json,
            confidence_baseline_json, caveats_json, metadata_json, created_at, updated_at
        )
        SELECT old.id, matches.user_id, old.match_id, old.player_key, old.player_name,
            old.player_steamid, old.source, old.source, '1.0.0', 'player_match',
            'legacy_unverified', old.source_parser_artifact_id, old.source_event_set_id,
            old.metrics_json, old.confidence_baseline_json, old.caveats_json,
            old.metadata_json, old.created_at, old.updated_at
        FROM metric_snapshots_legacy_v1 AS old
        JOIN matches ON matches.id = old.match_id;
        DROP TABLE metric_snapshots_legacy_v1;
        CREATE INDEX ix_metric_snapshots_owner_user_id ON metric_snapshots(owner_user_id);
        CREATE INDEX ix_metric_snapshots_semantic_version ON metric_snapshots(semantic_version);
        CREATE INDEX ix_metric_snapshots_validation_status ON metric_snapshots(validation_status);
        CREATE INDEX ix_metric_snapshots_metric_domain ON metric_snapshots(metric_domain);
        """
    )


def rollback(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_snapshots)")}
    if "semantic_version" not in columns:
        return
    collision = connection.execute(
        """SELECT match_id, player_key, source, COUNT(*)
           FROM metric_snapshots GROUP BY match_id, player_key, source HAVING COUNT(*) > 1 LIMIT 1"""
    ).fetchone()
    if collision:
        raise RuntimeError("rollback requires removal of appended semantic versions after verified backup")
    connection.executescript(
        """
        ALTER TABLE metric_snapshots RENAME TO metric_snapshots_contract_v2;
        CREATE TABLE metric_snapshots (
            id INTEGER PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES matches(id),
            player_key VARCHAR(255) NOT NULL,
            player_name VARCHAR(255),
            player_steamid VARCHAR(32),
            source VARCHAR(80) NOT NULL,
            source_parser_artifact_id INTEGER REFERENCES demo_parse_artifacts(id),
            source_event_set_id VARCHAR(255),
            metrics_json TEXT NOT NULL,
            confidence_baseline_json TEXT NOT NULL,
            caveats_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT uq_metric_snapshot_match_player_source UNIQUE (match_id, player_key, source)
        );
        INSERT INTO metric_snapshots
        SELECT id, match_id, player_key, player_name, player_steamid, source,
            source_parser_artifact_id, source_event_set_id, metrics_json,
            confidence_baseline_json, caveats_json, metadata_json, created_at, updated_at
        FROM metric_snapshots_contract_v2;
        DROP TABLE metric_snapshots_contract_v2;
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--direction", choices=("upgrade", "rollback"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()
    database = args.database.resolve()
    if database == PRODUCTION_DB and not (
        args.allow_production and os.environ.get("H01A_M03_PRODUCTION_AUTHORIZED") == "YES"
    ):
        raise SystemExit("production database migration is forbidden without explicit M03 authorization")
    if not database.exists():
        raise SystemExit(f"database does not exist: {database}")
    if args.dry_run:
        print(f"METRIC_SNAPSHOT_MIGRATION_DRY_RUN direction={args.direction} database={database}")
        return 0
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        with connection:
            (upgrade if args.direction == "upgrade" else rollback)(connection)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"integrity check failed: {integrity}")
    finally:
        connection.close()
    print(f"METRIC_SNAPSHOT_MIGRATION_OK direction={args.direction} database={database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
