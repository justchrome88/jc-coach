# Metrics Agent Entry Point

This fixed-path file exists only for agent-policy discovery. It is not a metric
registry, application contract, or Product source of truth.

Before changing metric code, contracts, or human metric documentation, read:

- `project_docs/metrics/README.md` and the applicable human contract or policy;
- `app/contracts/metrics/registry/metrics.json` and applicable runtime contract;
- `project_control/agents/guardians/METRICS_GUARDIAN.md` and
  `project_control/agents/PROJECT_OPERATING_PROTOCOL.md`.

Root `AGENTS.md` and this nested policy both apply.

- Preserve a formula's semantic version or increment it; never silently overwrite prior semantics.
- UI output and external comparators are evidence, never sole ground truth.
- Update the registry, domain contract, tests, golden evidence, and generated catalog together.
- Preserve owner, match, player, parser artifact, event-set, and semantic-version lineage.
- State whether a change requires snapshot or downstream backfill; never overwrite historical meaning in place.
- Run `.venv/bin/python scripts/metrics_registry.py --check`, the applicable
  metric tests, semantic/golden fixtures, and `git diff --check`.
- Record unresolved semantics and rejected alternatives in a PM investigation
  or change report; do not add task reports under `project_docs/metrics/`.
- Disputed or unvalidated values must not silently become hard coach, hypothesis, mission, or progress claims.
- Coach-domain changes must also update
  `app/contracts/metrics/coach-domain-metric-requirements.json`, the Coach
  Metric Pack contract/evidence matrix under `project_docs/metrics/coach/`, an
  independent real-demo golden fixture, and
  `scripts/validate_coach_metric_pack.py`.
Production parsing, recomputation, backfill, DB mutation, and coach mutation still require explicit task authorization.
