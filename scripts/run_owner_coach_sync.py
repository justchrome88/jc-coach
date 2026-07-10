from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and sys.prefix == sys.base_prefix:
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.owner_coach_sync import (  # noqa: E402
    DEFAULT_MAX_NEW_MATCHES,
    run_owner_coach_sync,
)

FAILED_EXIT = 1
ALREADY_RUNNING_EXIT = 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    output_path = Path(args.output_json).expanduser()

    db = SessionLocal()
    try:
        result = run_owner_coach_sync(
            db,
            owner_user_id=args.owner_user_id,
            max_new_matches=args.max_new_matches,
            dry_run=args.dry_run,
            continue_on_match_error=args.continue_on_match_error,
            specific_sharecode=args.specific_sharecode,
        )
    finally:
        db.close()

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"Could not write owner sync JSON: {type(exc).__name__}", file=sys.stderr)
        return FAILED_EXIT

    run = result["run"]
    totals = result["totals"]
    print(
        "Owner coach sync "
        f"status={run['status']} owner_user_id={run['owner_user_id']} "
        f"discovered={totals['discovered']} new={totals['new']} "
        f"reused={totals['reused']} failed={totals['failed']} output={output_path}"
    )
    if run["status"] in {"failed", "blocked"}:
        return FAILED_EXIT
    if run["status"] == "already_running":
        return ALREADY_RUNNING_EXIT
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one owner-scoped headless import-to-coach synchronization cycle.")
    parser.add_argument("--owner-user-id", type=int, required=True)
    parser.add_argument("--max-new-matches", type=int, default=DEFAULT_MAX_NEW_MATCHES)
    parser.add_argument("--dry-run", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--continue-on-match-error",
        dest="continue_on_match_error",
        action="store_true",
        default=True,
    )
    mode.add_argument("--strict", dest="continue_on_match_error", action="store_false")
    parser.add_argument("--specific-sharecode")
    parser.add_argument("--output-json", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
