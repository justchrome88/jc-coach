# JC Coach Metric Source of Truth

This directory is the canonical metric knowledge base. Code remains executable behavior; disagreements between code and these contracts are defects or explicitly documented legacy semantics, not permission to guess.

## Authority map

- `registry/metrics.json`: machine-readable inventory, identity, semantics, versions, persistence, consumers, truth status, and discrepancies.
- `contracts/*.md`: normative domain rules and boundaries shared by multiple metrics.
- `METRIC_DATA_LINEAGE.md`: identities and joins from retained demo through UI and coach.
- `METRIC_GOVERNANCE.md`: authority, confidence, validation, and quarantine rules.
- `METRIC_CHANGE_POLICY.md`: add/change/deprecate/version/backfill workflow.
- `GROUND_TRUTH_POLICY.md`: evidence hierarchy and comparator policy.
- `investigations/`: time-bound evidence; it does not redefine a contract by itself.
- `generated/METRIC_CATALOG.md`: reproducible view generated only from the registry.

`docs/METRICS.md` and `app/services/metric_truth.py` remain supporting legacy runtime policy until M02 reconciles them with this registry. They do not override a disputed registry entry.

## Change workflow

1. Identify the metric and domain contract; preserve identity and current semantic version.
2. Add independent evidence and an acceptance fixture. A test that repeats the implementation formula is insufficient.
3. For changed meaning, increment the semantic version and decide whether old snapshots are retained, quarantined, or backfilled into a new version.
4. Update registry, contract, tests, golden evidence, and catalog together.
5. Run `.venv/bin/python scripts/metrics_registry.py --write`, then `--check`, focused tests, semantic/golden fixtures, and `git diff --check`.

Validation without rewriting the catalog: `.venv/bin/python scripts/metrics_registry.py --check`.
