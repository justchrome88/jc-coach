from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and sys.prefix == sys.base_prefix:
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.ingestion.steam import (  # noqa: E402
    is_stale_steam_import_all_job,
    mark_steam_import_all_job_interrupted,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explicit operator repair for one stale running steam_import_all ImportJob."
    )
    parser.add_argument("--job-id", type=int, required=True, help="ImportJob id to mark interrupted.")
    parser.add_argument(
        "--i-have-backup",
        action="store_true",
        help="Required acknowledgement that the production DB was backed up first.",
    )
    parser.add_argument(
        "--confirm-interrupt",
        action="store_true",
        help="Required acknowledgement that this selected job should be marked interrupted.",
    )
    parser.add_argument(
        "--reason",
        default="Operator marked stale steam_import_all job interrupted after WP-014C SIGKILL.",
        help="Reason written to ImportJob.error_message and result_json.",
    )
    args = parser.parse_args()

    if not args.i_have_backup or not args.confirm_interrupt:
        parser.error("Refusing repair without --i-have-backup and --confirm-interrupt.")

    db = SessionLocal()
    try:
        from app.db.models import ImportJob

        job = db.get(ImportJob, args.job_id)
        if job is None:
            raise SystemExit(f"ImportJob #{args.job_id} was not found.")
        if job.provider != "steam" or job.job_type != "steam_import_all":
            raise SystemExit(f"ImportJob #{args.job_id} is not a steam_import_all job.")
        if job.status != "running":
            raise SystemExit(f"ImportJob #{args.job_id} is {job.status}, not running.")
        if not is_stale_steam_import_all_job(job):
            raise SystemExit(f"ImportJob #{args.job_id} is not stale by configured timeout.")
        mark_steam_import_all_job_interrupted(db, job, reason=args.reason)
        print(f"Marked steam_import_all ImportJob #{args.job_id} interrupted.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
