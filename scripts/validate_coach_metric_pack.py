from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/metrics/registry/metrics.json"
DOMAIN_PATH = ROOT / "docs/metrics/coach/coach-domain-metric-requirements.json"
GOLDEN_PATH = ROOT / "tests/fixtures/metrics/coach_metric_real_demo_corpus.json"
IMPLEMENTATION_PATH = ROOT / "app/services/coach_metric_pack.py"
VERSION = "3.0.0"
FORBIDDEN_HARD_KEYS = {"damage", "utility_damage", "headshot_rate", "latest_snapshot"}

PACK_KEYS = {
    "rounds_played",
    "kills",
    "deaths",
    "kd_ratio",
    "kills_per_round",
    "ordinary_assists",
    "flash_assists",
    "combined_assists",
    "headshot_kills",
    "headshot_kill_rate",
    "survival_rate",
    "effective_enemy_damage",
    "adr",
    "kast",
    "opening_duel_attempts",
    "opening_duel_wins",
    "opening_duel_losses",
    "opening_duel_win_rate",
    "multi_kill_rounds",
    "trade_kills",
    "traded_deaths",
    "trade_success_rate",
    "he_detonations",
    "smoke_detonations",
    "flash_detonations",
    "fire_grenade_detonations",
    "enemy_he_damage",
    "enemy_fire_damage",
    "effective_enemy_utility_damage",
    "utility_damage_per_round",
    "enemies_effectively_flashed",
    "effective_enemy_flash_duration",
    "smokes_used",
    "accepted_shots",
    "accepted_hits",
    "shot_accuracy",
    "head_hits",
    "hit_based_headshot_rate",
    "first_shots",
    "first_shot_hits",
    "first_bullet_accuracy",
    "engagements_with_kill",
    "first_shot_to_kill_ms",
    "first_damage_to_kill_ms",
}


def main() -> int:
    errors: list[str] = []
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8")) if GOLDEN_PATH.exists() else {}
    by_key = {item["metric_key"]: item for item in registry["metrics"]}

    missing_registry = sorted(PACK_KEYS - set(by_key))
    if missing_registry:
        errors.append(f"registry missing pack keys: {missing_registry}")
    for key in sorted(PACK_KEYS & set(by_key)):
        item = by_key[key]
        if item.get("semantic_version") != VERSION:
            errors.append(f"{key}: expected semantic version {VERSION}")
        if item.get("validation_status") != "validated" or item.get("consumer_policy") != "trusted":
            errors.append(f"{key}: not trusted/validated")
        paths = item.get("implementation_entrypoints") or []
        if not any("coach_metric_pack.py" in str(path) for path in paths):
            errors.append(f"{key}: authoritative implementation path missing")

    families = manifest.get("families") or []
    if manifest.get("current_coach_domains") != ["performance", "utility"]:
        errors.append("current coach domain freeze is not performance+utility")
    family_names = {item.get("hypothesis_family") for item in families}
    if family_names != {"survival_opening", "bad_fight_trade", "utility_value"}:
        errors.append(f"unexpected hypothesis families: {sorted(family_names)}")
    domain_leaf_keys = {
        key
        for item in families
        for key in item.get("required_leaf_metric_keys", [])
    }
    if domain_leaf_keys - set(by_key):
        errors.append(f"domain leaf keys missing registry entries: {sorted(domain_leaf_keys - set(by_key))}")
    forbidden = sorted(domain_leaf_keys & FORBIDDEN_HARD_KEYS)
    if forbidden:
        errors.append(f"forbidden generic domain leaf keys: {forbidden}")
    if manifest.get("active_mission_required_metrics") != ["effective_enemy_utility_damage"]:
        errors.append("active mission dependency is not the explicit validated utility key")

    if not IMPLEMENTATION_PATH.exists():
        errors.append("authoritative implementation file missing")
    if golden.get("schema_version") != "coach-metric-real-demo-corpus-v1":
        errors.append("real-demo golden corpus missing or wrong version")
    fixtures = golden.get("fixtures") or []
    if len(fixtures) < 5:
        errors.append("real-demo golden corpus requires at least five fixtures")
    if 124 not in {item.get("match_id") for item in fixtures}:
        errors.append("real-demo golden corpus must include match 124")
    for item in fixtures:
        if not item.get("demo_sha1") or not item.get("ledger_checksum"):
            errors.append(f"match {item.get('match_id')}: missing demo or ledger checksum")
        expected = item.get("expected_metrics") or {}
        missing = PACK_KEYS - set(expected) - set(item.get("unavailable_keys") or [])
        if missing:
            errors.append(f"match {item.get('match_id')}: golden coverage missing {sorted(missing)}")
        if item.get("independent_evidence_method") != "audited_low_level_event_ledger":
            errors.append(f"match {item.get('match_id')}: independent evidence method not recorded")

    catalog = subprocess.run(
        [sys.executable, str(ROOT / "scripts/metrics_registry.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if catalog.returncode:
        errors.append(f"catalog/registry reproducibility failed: {catalog.stdout}{catalog.stderr}".strip())

    if errors:
        print("COACH_METRIC_PACK_VALIDATION=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "COACH_METRIC_PACK_VALIDATION=PASS "
        f"metrics={len(PACK_KEYS)} families={len(families)} golden_demos={len(fixtures)} version={VERSION}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
