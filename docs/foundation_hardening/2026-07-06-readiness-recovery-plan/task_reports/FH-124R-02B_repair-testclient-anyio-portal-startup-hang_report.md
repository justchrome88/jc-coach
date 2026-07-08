# FH-124R-02B Repair TestClient AnyIO Portal Startup Hang Report

Date: 2026-07-08

Task: `FH-124R-02B Repair TestClient AnyIO portal startup hang`

Task type: Execution task - focused test/runtime repair

Output mode: File-backed report

## Verdict

Executor verdict: `PASS_WITH_WARNINGS`

The focused repair succeeded: the two known reproducing tests pass under the
required timeout, the full `tests` suite passes under the required timeout, and
the accepted local quality gate passes.

Warnings:

- Pytest still emits the upstream
  `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
  No package installation was authorized or performed.
- Interim repair attempts reproduced additional hangs before the final patch.
  The final required evidence commands all pass.

H1 final readiness passed: `NO`

This task does not claim final readiness. H1 final readiness remains failed
pending a future accepted final-gate path. H2, WP-018 restart,
`WL-FH-000-036` closure and major CS2 feature work remain blocked.

## Context Used

Hot/task context read:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/HANDOFF.md`
- `/opt/jc-coach-pm/AGENTS.md`
- `/opt/jc-coach-pm/outbox/2026-07-08_FH-124R-02B_task-card.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`

Task-specific Warm/evidence context read:

- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md`
- `/opt/jc-coach-pm/reviews/2026-07-08_FH-124R-02A_review.md`

Context manifest used: `true`.

Broad Cold context avoided: `true`.

External documentation:

- Context7 `/kludex/starlette` docs were consulted for Starlette `TestClient`
  behavior. The docs state that `TestClient` must be used as a context manager
  to run lifespan, and that `backend` / `backend_options` are passed to
  `anyio.start_blocking_portal()`.

## Root Cause And Repair

Best-supported root cause:

- In the current local Python/dependency set, AnyIO's blocking thread helpers
  hang:
  - `anyio.from_thread.start_blocking_portal(...).call(...)` hangs.
  - `anyio.to_thread.run_sync(...)` hangs.
- Starlette/FastAPI `TestClient.__enter__` uses AnyIO's blocking portal, which
  explains the FH-124R-02A stack in `starlette.testclient.TestClient.__enter__`.
- FastAPI also dispatches sync endpoints/dependencies through
  `anyio.to_thread.run_sync`, so a replacement client still hung until the
  pytest harness avoided that broken thread helper.

Repair:

- Added a pytest-only compatibility patch in `tests/conftest.py`.
- During pytest startup, `fastapi.testclient.TestClient` and
  `starlette.testclient.TestClient` are patched to `PortalFreeTestClient`.
- `PortalFreeTestClient` preserves context-manager lifespan execution and sync
  HTTP request coverage, but drives ASGI requests through `anyio.run()` instead
  of Starlette's blocking portal.
- During pytest only, `anyio.to_thread.run_sync` is patched to execute sync
  callables inline. This avoids the local worker-thread hang for app routes and
  dependencies used by deterministic tests.

Runtime/product code was not changed.

## Files Changed

- `tests/conftest.py`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02B_repair-testclient-anyio-portal-startup-hang_report.md`

## Command Evidence

Commands were run from `/opt/jc-coach`.

| Command | Timeout | Exit | Result | Evidence excerpt |
|---|---:|---:|---|---|
| `git status --short` | none | `0` | `PASS` | No output before work; main repo clean. |
| `.venv/bin/python scripts/project_gate.py preflight` | none | `0` | `PASS` | Branch `agentdev`; `git status --short -uall` had no output; production DB SHA observed read-only as `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `.venv/bin/python scripts/project_gate.py changed` | none | `0` | `PASS` | `(none)` changed/untracked before implementation; activated guardian `PM_ORCHESTRATOR`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 120s .venv/bin/pytest tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state tests/test_web_smoke.py::test_health_endpoint -vv -ra --durations=20 -p no:cacheprovider` | `120s` | `0` | `PASS` | `2 passed, 1 warning in 0.23s`; both reproducing tests passed. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 420s .venv/bin/pytest tests -q -p no:cacheprovider` | `420s` | `0` | `PASS` | `250 passed, 1 warning in 10.99s`; full test coverage preserved. |
| `timeout 420s .venv/bin/python scripts/local_quality_gate.py` | `420s` | `0` | `PASS` | `LOCAL_QUALITY_GATE=PASS`; full safe pytest `250 passed`; Ruff `All checks passed!`; `git diff --check` passed; postflight passed. |
| `.venv/bin/python scripts/project_gate.py postflight` | none | `0` | `PASS` | Final post-report changed paths: `M tests/conftest.py` and `?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02B_repair-testclient-anyio-portal-startup-hang_report.md`; production DB SHA unchanged/observed read-only as `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `git diff --check` | none | `0` | `PASS` | No output. |

Additional bounded diagnostic evidence during implementation:

- A minimal `with TestClient(FastAPI())` script timed out after printing
  `before`, supporting that the issue was not JC Coach lifespan logic.
- `anyio.from_thread.start_blocking_portal(...).call(...)` timed out after the
  portal was entered.
- `anyio.to_thread.run_sync(lambda: 123)` timed out after printing
  `to thread start`.
- An async FastAPI endpoint returned normally under a direct ASGI call, while a
  sync FastAPI endpoint hung, supporting the `anyio.to_thread.run_sync` part of
  the repair.

## Acceptance Checks

- Two known reproducing tests passed: `YES`.
- Full-suite coverage preserved: `YES`, `tests` collected and ran all 250 tests.
- Full suite passed under timeout: `YES`.
- Accepted local quality gate passed: `YES`.
- H1 final readiness remains failed pending future accepted final-gate path:
  `YES`.
- H2 remains blocked: `YES`.
- WP-018 restart remains blocked: `YES`.
- `WL-FH-000-036` closure remains blocked: `YES`.
- Major CS2 feature work remains blocked: `YES`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK` was not set to `YES`.

## Docs Update Checklist

| Checklist item | Status | Reason |
|---|---|---|
| Hot/current status docs | `checked; no update required` | Task card forbids status/readiness promotion updates; H1 remains failed. |
| WP registry/status/handoff docs | `checked; no update required` | No WP promotion, H2 run, WP-018 restart or blocker closure occurred. |
| Navigation docs | `not applicable` | No new canonical/navigation doc was created. |
| Task-relevant domain docs | `checked; no update required` | Repair was confined to pytest runtime compatibility and this task report. |
| Documentation Steward | `checked; no update required` | No Hot/Warm/control-plane docs changed; report includes required checklist. |
| Deferred docs follow-up | `none` | No docs follow-up is required by this repair. |

## Safety Declarations

Forbidden actions detected: `false`.

- Production DB mutation: `NO`.
- Production DB copy: `NO`.
- Schema mutation, migration artifact edit, startup schema behavior change or
  migration-engine adoption: `NO`.
- Production data mutation: `NO`.
- Production DB SHA observed read-only through project gates:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Live Steam/Valve import: `NO`.
- Parser job, evaluator job or manual evaluator job: `NO`.
- Demo download, decompression, raw-demo move/delete/compression or upload
  operation: `NO`.
- Deploy/service/nginx/systemd change or restart: `NO`.
- Package installation: `NO`.
- Secrets printed: `NO`.
- `git add`: `NO`.
- Commit: `NO`.
- Push: `NO`.
- H2 run: `NO`.
- WP-018 restarted: `NO`.
- `WL-FH-000-036` closed: `NO`.
- Major CS2 work unlocked: `NO`.

## Blockers

No blocker prevents completing this focused repair.

H1 final readiness remains blocked until a future accepted final-gate path runs
and passes under its own task card.

## Discovery Result

```yaml
discovery_result:
  completeness_estimate: "High for the focused TestClient/AnyIO pytest hang repair; final readiness remains unproven because H1 was not rerun by this task."
  missing_items_found: false
  followup_required: true
  followup_tasks_recommended:
    - proposed_id: "FH-124R-03"
      title: "Rerun H1 final readiness after TestClient AnyIO repair"
      reason: "The focused repair restored full-suite pytest and local quality gate evidence, but this task was not authorized to claim H1 final readiness PASS."
      risk: "P1"
      suggested_scope: "tests"
      needs_user_decision: false
```

## Machine Summary

```text
EXECUTOR_VERDICT=PASS_WITH_WARNINGS
EXECUTOR_REPORT_PATH=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02B_repair-testclient-anyio-portal-startup-hang_report.md
FORBIDDEN_ACTIONS_DETECTED=false
NEEDS_USER=false
```
