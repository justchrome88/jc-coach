# POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API Report

Date: 2026-07-08

Task: `POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API`

Task type: tests / validation / focused technical-confidence pass

## Verdict

Executor verdict: `PASS_WITH_WARNINGS`

The focused technical-confidence pass completed.

What changed:

- Added focused live `TestClient` API-token contract tests in
  `tests/test_endpoint_contracts.py`.
- Deepened `/api/coach/ai/result` and `/api/coach/ai/result/latest` coverage
  for:
  - API-token authenticated live HTTP dispatch.
  - `404` translation for missing latest AI result.
  - `400` translation for empty submitted AI output without persistence.
  - successful write/read round trip through the isolated pytest SQLite DB.
  - existing no-schema payload snapshot metadata exposed through serialized
    report JSON (`payload_hash`, `payload_matches_count`,
    `metadata.payload_summary.matches_count`, validation metadata).

Warnings:

- The upstream Starlette/httpx TestClient deprecation warning remains visible:
  `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
  The task card forbade package/dependency changes, so this is explicitly
  classified as an accepted limitation / future dependency-maintenance
  follow-up for this pass.
- No production/app code change was made. If the project wants to remove the
  pytest-only `PortalFreeTestClient` compatibility shim or the Starlette/httpx
  warning, that requires a separately authorized dependency/test-harness task.

No product readiness unlock occurred. The preserved state remains:

- `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`
- `NEXT_LANE=POST_FOUNDATION_AUDIT_AND_STABILIZATION`
- `READY_FOR_MAJOR_CS2_FEATURE_WORK=NO`

## Context And Scope

Context manifest used: `true`.

Task identity preflight:

- Exactly one active non-dotfile PM outbox card was present:
  `/opt/jc-coach-pm/outbox/2026-07-08_POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API_task-card.md`.
- Active outbox card, `indexes/current_context_manifest.json`, and
  `indexes/task_index.json` agreed on
  `POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API`.

Hot/task context read:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/HANDOFF.md`
- `/opt/jc-coach-pm/AGENTS.md`
- `/opt/jc-coach-pm/outbox/2026-07-08_POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API_task-card.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`
- `/opt/jc-coach-pm/indexes/task_index.json`
- `/opt/jc-coach-pm/memory/PROJECT_MEMORY_COMPACT.md`
- `/opt/jc-coach-pm/memory/FOUNDATION_HARDENING_MEMORY.md`
- `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/POST_FOUNDATION_REPAIR_SEQUENCE_PLAN.md`

Task-relevant evidence/docs read:

- `docs/API_CONTRACTS.md`
- `docs/ARCHITECTURE.md` searched for API/auth/test ownership context.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02B_repair-testclient-anyio-portal-startup-hang_report.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-03_h1-final-readiness-rerun-after-testclient-repair_report.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-AUDIT-01_full-foundation-defect-warning-inventory-audit_report.md`
- PM warning ledger rows for `WL-FH-000-019` and `WL-FH-000-023` found via
  targeted `rg`.

Broad Warm/Cold context avoided: `true`.

External docs:

- Context7 `/fastapi/fastapi` was consulted for FastAPI `TestClient` testing
  behavior. The relevant current docs confirm FastAPI uses `TestClient` for
  route tests and that `httpx` is required for it.

## Files Changed

- `tests/test_endpoint_contracts.py`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API_report.md`

No app/product code, PM repo files, dependency files, schema files, migration
files, deploy files or service configuration files were changed.

## Acceptance Coverage

Snapshot/TestClient/httpx follow-up:

- Local evidence now includes additional live `TestClient` route coverage in
  `tests/test_endpoint_contracts.py`.
- The pytest-only `PortalFreeTestClient` shim remains in `tests/conftest.py`
  from FH-124R-02B. It was not changed.
- The Starlette/httpx deprecation warning still appears in focused and full
  test runs. Because package installation/dependency changes were forbidden,
  this is classified as an accepted limitation / follow-up rather than fixed in
  this task.

`WL-FH-000-019` API validation depth:

- Improved with live API-token route tests for AI coach result persistence and
  service exception translation.
- Remaining limitation: this is not an exhaustive service-level API matrix for
  every route group.

`WL-FH-000-023` live ASGI/TestClient coverage limitation:

- Improved with safe live HTTP `TestClient` coverage for owner/API-token
  protected JSON API routes.
- Existing `tests/test_web_smoke.py` and `tests/test_security.py` continue to
  cover public/owner pages, CSRF rejection, API auth rejection and API-token
  write access.
- Remaining limitation: high-risk import/parser/Steam live work was not run and
  remains forbidden without explicit authorization.

Existing safety gates:

- Fail-closed API auth and CSRF behavior remained covered by existing focused
  tests and passed.
- Local quality gate passed after a one-line import-order fix in the edited
  test file.

## Command Evidence

Commands were run from `/opt/jc-coach`.

| Command | Exit | Result | Evidence excerpt |
|---|---:|---|---|
| `git status --short` | `0` | `PASS` | No output before work; main repo clean. |
| PM outbox / manifest / task-index preflight commands | `0` | `PASS` | One active outbox card; task id matched manifest and task index. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 120s .venv/bin/pytest tests/test_endpoint_contracts.py -q -p no:cacheprovider` | `0` | `PASS` | `8 passed, 1 warning in 0.31s`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 180s .venv/bin/pytest tests/test_security.py tests/test_web_smoke.py tests/test_endpoint_contracts.py -q -p no:cacheprovider` | `0` | `PASS` | `29 passed, 1 warning in 1.03s`. |
| `.venv/bin/python scripts/project_gate.py changed` | `0` | `PASS` | Changed file: `M tests/test_endpoint_contracts.py`; guardians: `PM_ORCHESTRATOR`, `TEST_GUARDIAN`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 420s .venv/bin/pytest tests -q -p no:cacheprovider` | `0` | `PASS` | `253 passed, 1 warning in 11.00s`. |
| `timeout 420s .venv/bin/python scripts/local_quality_gate.py` | `1` | `FAIL_THEN_FIXED` | Initial run failed only on Ruff `I001` import ordering in the edited test file; test suite itself passed as `253 passed, 1 warning`. |
| `.venv/bin/ruff check tests/test_endpoint_contracts.py --no-cache` | `0` | `PASS` | `All checks passed!` after import ordering fix. |
| `timeout 420s .venv/bin/python scripts/local_quality_gate.py` | `0` | `PASS` | `LOCAL_QUALITY_GATE=PASS`; full safe pytest `253 passed, 1 warning`; Ruff passed; `git diff --check` passed; postflight passed. |
| `git diff --check` | `0` | `PASS` | No output after report creation. |
| `.venv/bin/python scripts/project_gate.py postflight` | `0` | `PASS` | Final changed paths: `M tests/test_endpoint_contracts.py` and this untracked report; guardians: `DOCUMENTATION_STEWARD`, `PM_ORCHESTRATOR`, `TEST_GUARDIAN`; production DB SHA observed read-only. |

The single repeated warning in pytest/local-gate output was the Starlette/httpx
TestClient deprecation warning described above.

Final `git status --short`:

```text
 M tests/test_endpoint_contracts.py
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API_report.md
```

## Safety Declarations

Forbidden actions detected: `false`.

- Production DB mutation: `NO`.
- Production DB copy: `NO`.
- Production DB schema mutation, migration artifact edit, startup schema
  behavior change or migration-engine implementation: `NO`.
- Production DB SHA observed read-only through local quality gate/project-gate
  evidence:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Test DB used: pytest SQLite DB under `/tmp` via `tests/conftest.py`.
- Live Steam/Valve import: `NO`.
- Parser job, evaluator job or manual evaluator job on production data: `NO`.
- Demo download, raw-demo move/delete/compression or upload operation: `NO`.
- Persistent app reports generated: `NO`.
- Package install or dependency change: `NO`.
- Production/app code change: `NO`.
- Deploy/nginx/systemd/service config change or restart: `NO`.
- PM repo edit: `NO`.
- `git add`: `NO`.
- Commit: `NO`.
- Push: `NO`.
- `WP-018` restarted: `NO`.
- Counter-Strike product/feature work started: `NO`.
- Public/friends access unlocked: `NO`.
- System `v1.0` claimed or packaged: `NO`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK=YES`: `NO`.

## Blockers

No blocker prevented completing this focused technical-confidence pass.

## Residual Limitations And Follow-Up

The route/service/auth confidence is improved but not exhaustive. Remaining
coverage follow-ups should be scoped separately if needed:

- Full route/service validation matrix across every JSON API group.
- Additional live HTTP tests for recommendation mutation edge cases, Steam
  service exception translation and storage artifact writes using mocks/temp
  fixtures only.
- Dependency/test-harness maintenance to remove or replace the pytest-only
  TestClient shim and resolve the Starlette/httpx deprecation warning, if
  package/dependency changes are explicitly authorized.

```yaml
discovery_result:
  completeness_estimate: "Moderate-to-high for the focused technical-confidence pass; not exhaustive across every route group."
  missing_items_found: true
  followup_required: true
  followup_tasks_recommended:
    - proposed_id: "POST-FOUNDATION-REPAIR-P1-API-MATRIX-FOLLOWUP"
      title: "Expand route/service API validation matrix"
      reason: "This task added focused live API-token coverage, but it did not exhaustively cover every route group and service exception translation path."
      risk: "P1"
      suggested_scope: "tests"
      needs_user_decision: false
    - proposed_id: "POST-FOUNDATION-REPAIR-P2-TESTCLIENT-DEPENDENCY-MAINTENANCE"
      title: "Resolve TestClient httpx dependency warning"
      reason: "The Starlette/httpx deprecation warning remains because dependency/package changes were forbidden in this task."
      risk: "P2"
      suggested_scope: "tests"
      needs_user_decision: true
```

## Token / Cycle Metrics

- PM_CREATE tokens: `UNKNOWN`
- EXECUTOR tokens: `UNKNOWN`
- PM_REVIEW tokens: `UNKNOWN`
- Total cycle tokens: `UNKNOWN`
- Task verdict: `PASS_WITH_WARNINGS`
- Quality verdict: `PASS_WITH_WARNINGS`
- Number of broad reads avoided: `UNKNOWN`; broad doc tree reads and raw run
  logs were avoided.
- Context manifest used: `true`

## Machine Summary

```text
EXECUTOR_VERDICT=PASS_WITH_WARNINGS
EXECUTOR_REPORT_PATH=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/POST-FOUNDATION-REPAIR-P1-TECHNICAL-CONFIDENCE-SNAPSHOT-API_report.md
FORBIDDEN_ACTIONS_DETECTED=false
NEEDS_USER=true
```
