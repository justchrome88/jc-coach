> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/metrics/coach/ADDING_A_COACH_METRIC.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Adding a Coach Metric

1. Register the explicit leaf key in `registry/metrics.json`; never introduce a
   generic alias such as `damage`, `utility_damage`, `headshot_rate` or “latest”.
2. Write the contract: numerator, denominator, phase, participation, team,
   rounding, zero-denominator and aggregation behavior.
3. Name the raw/source evidence and classify whether the current event set is
   sufficient. Insufficient evidence means unavailable.
4. Increment semantic version whenever meaning, boundaries, identity or
   rounding changes. Preserve prior snapshots and artifacts.
5. Implement one authoritative calculation path and retain owner/match/player/
   parser/event-set provenance.
6. Add a compact independent golden fixture. Expected values must come from an
   audited low-level ledger or independent oracle, not the calculator under
   test.
7. Validate formula edges, real demos, missing-data non-claims and trusted
   consumer behavior.
8. Set an explicit consumer policy. Only validated allowed versions may reach
   coach, hypothesis, mission, progress, API or trusted UI payloads.
9. Plan append-only migration/backfill, idempotency identity, downstream
   reconciliation and rollback before production mutation.
10. Regenerate the catalog and run
    `.venv/bin/python scripts/validate_coach_metric_pack.py`, the focused tests,
    registry check, Ruff, the local quality gate and `git diff --check`.
