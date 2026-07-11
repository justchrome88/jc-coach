"""Read-only loader for JSON runtime contracts under ``app/contracts``."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = ROOT / "app" / "contracts"


@cache
def load_runtime_contract(relative_path: str) -> dict[str, Any]:
    path = (CONTRACT_ROOT / relative_path).resolve()
    if path != CONTRACT_ROOT and CONTRACT_ROOT not in path.parents:
        raise ValueError("Runtime contract path must remain under app/contracts.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Runtime contract must be a JSON object: {relative_path}")
    return payload


def metric_registry_contract() -> dict[str, Any]:
    return load_runtime_contract("metrics/registry/metrics.json")
