# JC Coach

JC Coach is a controlled personal AI coach for CS2. The current `v0.9` backend
has an immutable 30-match baseline, real LLM proposals, and exactly two coach
domains: `impact_leak` and `bad_fight_selection`. The next Product work is
service-boundary consolidation, then a minimal functional two-mission UI and a
30+10 replay. Package version `0.1.0` remains intentionally independent.

## Repository map

- `app/` — application code; runtime prompts, schemas, registries, and machine
  contracts live under `app/contracts/`.
- `tests/` — automated behavior and regression coverage.
- `scripts/` — repository gates and bounded operational tools.
- `project_docs/` — canonical human Product, architecture, metric, operation,
  and acceptance documentation.
- `project_control/` — current status, roadmap, registry, checklists, and agent
  controls.
- `docs/` — fixed-path agent compatibility shell only.
- `_legacy_archive/` — preserved, noncanonical historical material.

Start with [current status](project_control/status/CURRENT_STATUS.md), the
[roadmap](project_control/planning/VERSION_ROADMAP.md), the
[work-package registry](project_control/planning/WP_REGISTRY.md), and the
[master checklist](project_control/checklists/MASTER_WP_CHECKLIST.md). Human
documentation starts at [project_docs/README.md](project_docs/README.md), and
the safety contract is [AGENTS.md](AGENTS.md).

Run the full safe suite with
`APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`;
run the complete local gate with `.venv/bin/python scripts/local_quality_gate.py`.

The package-level code map will be updated by R02A3. Operational configuration
remains at the repository root and under `deploy/`.
