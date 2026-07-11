#!/usr/bin/env python3
"""Atomically generate the declared coach-domain contract from runtime definitions."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.services.coach_domain_model import runtime_coach_domain_contract

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "app/contracts/coach/coach-domain-model.json"


def main() -> int:
    content = json.dumps(runtime_coach_domain_contract(), ensure_ascii=False, indent=2) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(f".{OUTPUT.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, OUTPUT)
    print(f"COACH_DOMAIN_CONTRACT={OUTPUT}")
    print("COACH_DOMAIN_CONTRACT_RESULT=written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
