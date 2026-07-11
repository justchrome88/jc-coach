# Metrics Agent Contract

Before touching metric code, read `README.md`, `registry/metrics.json`, and the applicable contract under `contracts/`.

- Preserve a formula's semantic version or increment it; never silently overwrite prior semantics.
- UI output and external comparators are evidence, never sole ground truth.
- Update the registry, domain contract, tests, golden evidence, and generated catalog together.
- Preserve owner, match, player, parser artifact, event-set, and semantic-version lineage.
- State whether a change requires snapshot or downstream backfill; never overwrite historical meaning in place.
- Run `.venv/bin/python scripts/metrics_registry.py --check`, the applicable metric tests, semantic/golden fixtures, and `git diff --check`.
- Record unresolved semantics and rejected alternatives in an investigation or change report.
- Disputed or unvalidated values must not silently become hard coach, hypothesis, mission, or progress claims.
- Coach-domain changes must also update `coach/coach-domain-metric-requirements.json`,
  the Coach Metric Pack contract/evidence matrix, an independent real-demo
  golden fixture, and `scripts/validate_coach_metric_pack.py`.
- Current trusted coach consumers select explicit semantic version `3.0.0`
  leaf keys. Generic `damage`, `utility_damage`, `headshot_rate`, and “latest
  snapshot” aliases are forbidden for new hard claims.

Production parsing, recomputation, backfill, DB mutation, and coach mutation still require explicit task authorization.
