#!/usr/bin/env python3
"""Create H01B-R02 append-only tables; no existing row is rewritten."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.config import PRODUCTION_DB_PATH
from app.db import models  # noqa: F401
from app.db.session import Base

TABLES = {"coach_evidence_baselines", "ai_domain_analyses", "coach_mission_proposals", "coach_domain_slots"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--authorized-task")
    args = parser.parse_args()
    path = args.database.resolve()
    if args.apply and path == PRODUCTION_DB_PATH and args.authorized_task != "H01B-R02":
        raise SystemExit("production migration requires --authorized-task H01B-R02")
    engine = create_engine(f"sqlite:///{path}", future=True)
    before = set(inspect(engine).get_table_names())
    print("planned_new_tables=" + ",".join(sorted(TABLES - before)))
    if not args.apply:
        print("result=DRY_RUN")
        return
    Base.metadata.create_all(engine)
    after = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        integrity = connection.scalar(text("PRAGMA integrity_check"))
        fk_rows = list(connection.execute(text("PRAGMA foreign_key_check")))
    if not TABLES.issubset(after) or integrity != "ok" or fk_rows:
        raise SystemExit("post_migration_invariant_failed")
    print("created_tables=" + ",".join(sorted(TABLES - before)))
    print("integrity=ok")
    print("foreign_key_violations=0")
    print("result=APPLIED")


if __name__ == "__main__":
    main()
