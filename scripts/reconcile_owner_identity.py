#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import create_engine

from app.config import get_settings
from app.services.owner_identity_reconciliation import OwnerReconciliationError, reconcile_owner_identity


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely reconcile one proven duplicate owner identity.")
    parser.add_argument("--legacy-user-id", type=int, required=True)
    parser.add_argument("--canonical-user-id", type=int, required=True)
    parser.add_argument("--identity-evidence", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-identity-merge", action="store_true")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    engine = create_engine(get_settings().database_url, future=True)
    try:
        result = reconcile_owner_identity(
            engine,
            legacy_user_id=args.legacy_user_id,
            canonical_user_id=args.canonical_user_id,
            identity_evidence=args.identity_evidence,
            apply=args.apply,
            confirm_identity_merge=args.confirm_identity_merge,
        )
    except OwnerReconciliationError as exc:
        result = {"schema_version": "owner-identity-reconciliation-v1", "applied": False, "error": str(exc)}
        exit_code = 2
    else:
        exit_code = 0
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output_json:
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
