#!/usr/bin/env python3
"""Run and persist a strict v2 clone-only timed integration replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.owner.timed_replay import run_timed_integration_replay
from app.services.shared.stage_observer import (
    REQUIRED_ACCEPTANCE_STAGES,
    STAGE_TRACE_SCHEMA_VERSION_V2,
    stage_observer,
    validate_stage_trace,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--accepted-source-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trace-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    database = args.database.resolve()
    trace_output = args.trace_output.resolve()
    summary_output = args.summary_output.resolve()
    for output in (trace_output, summary_output):
        if run_root not in output.parents:
            raise ValueError("replay_output_outside_run_root")

    events: list[dict[str, Any]] = []
    trace_id = f"H01B-R02A4T-{args.run_id}"
    database_uri = f"sqlite+pysqlite:///file:{database}?mode=ro&uri=true"
    engine = create_engine(database_uri, future=True)
    with Session(engine) as db:
        with stage_observer(
            events.append,
            schema_version=STAGE_TRACE_SCHEMA_VERSION_V2,
            trace_mode="integration_replay",
            trace_id=trace_id,
            run_id=args.run_id,
        ):
            summary = run_timed_integration_replay(
                db,
                database=database,
                run_root=run_root,
                accepted_source_root=args.accepted_source_root,
            )
    trace_validation = validate_stage_trace(events, required_stages=REQUIRED_ACCEPTANCE_STAGES)
    summary["trace_validation"] = trace_validation
    trace_output.parent.mkdir(parents=True, exist_ok=True)
    trace_output.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in events),
        encoding="utf-8",
    )
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"trace_validation": trace_validation, "summary_status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
