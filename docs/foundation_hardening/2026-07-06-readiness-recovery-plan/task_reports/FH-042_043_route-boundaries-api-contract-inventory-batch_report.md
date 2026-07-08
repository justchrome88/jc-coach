# FH-042/FH-043 Route Boundaries And API Contract Inventory Batch Report

Date: 2026-07-07
Executor: 02-Executor Codex
Task type: Documentation task
Mode: implementation
Output mode: file-backed

## Result

FH-042 verdict: PASS

FH-043 verdict: PASS

Batch verdict: PASS

## Scope Completed

- Updated `docs/ARCHITECTURE.md` with a current route boundary inventory from
  `app/main.py`, `app/api/routes.py` and `app/web/routes.py`.
- Created `docs/API_CONTRACTS.md` with a conservative current API contract
  inventory for core endpoints.
- Kept the work docs-only and descriptive. No route handlers, schemas,
  services, tests, runtime config, DB files or package/dependency files were
  changed.

## FH-042 Evidence - Route/Mutation Boundaries

- `docs/ARCHITECTURE.md` now distinguishes:
  - public application routes;
  - owner/session-gated web read routes;
  - owner/session-gated web mutation routes;
  - authenticated `/api/*` route groups;
  - read, session-write, DB-write, artifact-write, import/parser-write and
    Steam-import-write mutation classes;
  - auth/owner-sensitive, import/parser-sensitive, Steam-sensitive,
    recommendation-sensitive, report/AI-sensitive, DB-risk and artifact-risk
    routes.
- The new route section states that route restructuring, authentication
  boundary changes, request/response contract changes and mutation semantic
  changes require explicit future task scope.

## FH-043 Evidence - API Contract Inventory

- `docs/API_CONTRACTS.md` now documents:
  - common auth/owner expectations for public, web and `/api/*` routes;
  - CSRF/API-token expectations at the current middleware boundary;
  - endpoint/method, request/input summary, response/output summary and
    mutation/read class for core JSON API endpoints;
  - public/web boundary contracts for health, robots, landing, auth, language
    and Steam callback routes.
- Unknown or service-owned nested response details are marked as service-owned
  instead of being specified as stable contracts.
- The inventory is intentionally not presented as complete API versioning.

## Files Changed

- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACTS.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-042_043_route-boundaries-api-contract-inventory-batch_report.md`

## Checks Run

- `git status --short` before work:
  - no output; worktree was clean.
- `.venv/bin/python scripts/project_gate.py preflight`: PASS.
  - Reported clean status.
  - Reported production DB SHA:
    `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- `.venv/bin/python scripts/project_gate.py changed`: PASS.
  - Final changed/untracked files at check time:
    - `M docs/ARCHITECTURE.md`
    - `?? docs/API_CONTRACTS.md`
    - `?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-042_043_route-boundaries-api-contract-inventory-batch_report.md`
  - Activated guardians:
    - `DOCUMENTATION_STEWARD`
    - `PM_ORCHESTRATOR`
- `.venv/bin/python scripts/project_gate.py required-checks`: PASS.
  - Required checks listed: preflight, changed, required-checks, postflight and
    `git diff --check`.
  - Documentation Steward checklist was completed in this report.
- `git diff --check`: PASS.
- `.venv/bin/python scripts/project_gate.py postflight`: PASS.
  - Code/test/script change: no.
  - Activated guardians: `DOCUMENTATION_STEWARD`, `PM_ORCHESTRATOR`.
  - Changed/untracked files remained limited to the two allowed docs and this
    allowed report.
  - Reported production DB SHA:
    `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.

Not run:

- `pytest`, Ruff and `.venv/bin/python scripts/local_quality_gate.py` were not
  run because this task was docs-only and no code, scripts or tests changed.

## Documentation Steward Checklist

- Scope checked: only the two allowed docs and this allowed report were edited.
- Classifications:
  - `docs/ARCHITECTURE.md`: canonical/supporting architecture map.
  - `docs/API_CONTRACTS.md`: supporting API contract inventory.
  - this report: task evidence report.
- Hot/current status docs update: not required; this task did not change
  product status, readiness status, WP registry state or roadmap state.
- Navigation docs update: broad navigation docs were outside Task Card scope;
  a scoped pointer to `docs/API_CONTRACTS.md` was added in
  `docs/ARCHITECTURE.md` under Supporting Docs.
- Stale/conflicting docs found: none within the scoped files.
- Duplicate instructions found: none within the scoped files.
- Unreferenced docs checked: only scoped navigation for the new
  `docs/API_CONTRACTS.md`; no broad docs audit was performed.
- Recommended actions: use `docs/API_CONTRACTS.md` as input for FH-044/FH-047
  contract-test selection; do not treat it as complete API versioning.
- Closure verdict: PASS.
- Output mode used: file-backed.
- Automatic deletion/move/archive performed: no.

## Safety Declarations

- No production DB touch was performed by this task. The production DB SHA
  above was emitted by project gate commands as governance evidence only; no DB
  inspection, import, parser job, evaluator job or mutation was performed.
- No live Steam/Valve import was run.
- No parser jobs were run.
- No evaluator or manual evaluator jobs were run.
- No persistent app reports were generated.
- No service was started or restarted.
- No systemd, nginx, deploy, runner, no-run-log or model-routing config was
  changed.
- No route handlers, schemas, templates, services, DB models, startup behavior,
  tests, package files or dependency state were changed.
- No `git add`, commit or push was run.
- Forbidden actions detected: false.

## Blockers

None.

## Next WP

Proceed to the next scoped foundation hardening task, expected to use this
route/API inventory for FH-044/FH-047 contract-test selection without claiming
complete API versioning or changing runtime route behavior.
