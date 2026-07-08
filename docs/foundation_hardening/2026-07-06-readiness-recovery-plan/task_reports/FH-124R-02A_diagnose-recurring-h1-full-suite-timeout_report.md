# FH-124R-02A Diagnose Recurring H1 Full-Suite Timeout Report

Date: 2026-07-08

Task: `FH-124R-02A Diagnose recurring H1 full-suite timeout`

Task type: Audit / Review / Discovery - test/gate diagnostic

Mode: Diagnostic-only, bounded commands, fail-closed

Output mode: File-backed

## Verdict

Executor verdict: `PASS_WITH_WARNINGS`

H1 final readiness passed: `NO`

H1 final readiness remains failed. H2, WP-018 restart and major CS2 feature
work remain blocked pending a future passing H1 rerun, PM/User acceptance and
separate authorization. `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`.

Most likely slow/stalled area:

- Starlette/FastAPI `TestClient` startup in pytest, specifically
  `starlette.testclient.TestClient.__enter__` waiting on AnyIO portal startup.
- The first full-suite stall point is
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
- A comparison web smoke test, `tests/test_web_smoke.py::test_health_endpoint`,
  hangs with the same `TestClient.__enter__` / AnyIO portal stack. That makes
  the issue broader than coach-page route logic.

Collection is not the problem: pytest collected 250 tests in `0.26s`. The
full-suite timeout is also not explained by pytest quiet output alone: the
required verbose full-suite command timed out after printing the active test
name and before that test completed.

Root cause is not fixed by this task. This report only identifies the likely
stalled area with bounded diagnostic evidence.

## Context Used

Hot/task context read:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `/opt/jc-coach-pm/outbox/2026-07-08_FH-124R-02A_task-card.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`

Task-specific Warm/evidence context read:

- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-120_124R-02_h1-final-readiness-rerun_report.md`

Context manifest used: `true`.

Broad Cold context avoided: `true`.

External documentation:

- Context7 `/pytest-dev/pytest` docs were consulted for pytest behavior. The
  docs confirm that `--collect-only` collects without running tests, `-q` and
  `-vv` are verbosity controls, `--durations=N` reports slow tests and
  `faulthandler_timeout` dumps tracebacks of all threads when a test exceeds
  the configured duration.

## Required Command Evidence

Commands were run from `/opt/jc-coach`.

| Command | Timeout | Exit | Result | Evidence |
|---|---:|---:|---|---|
| `git status --short` | none | `0` | `PASS` | No output; main repo clean before work. |
| `.venv/bin/python scripts/project_gate.py preflight` | none | `0` | `PASS` | Branch `agentdev`; clean status; governance files present; production DB SHA observed read-only as `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `.venv/bin/python scripts/project_gate.py changed` | none | `0` | `PASS` | `(none)` changed/untracked; activated guardian `PM_ORCHESTRATOR`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 120s .venv/bin/pytest --collect-only tests -q -p no:cacheprovider` | `120s` | `0` | `PASS` | `250 tests collected in 0.26s`; warning from FastAPI/Starlette TestClient import was emitted. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 180s .venv/bin/pytest tests -vv -ra --durations=50 -p no:cacheprovider` | `180s` | `124` | `TIMEOUT` | Collected 250 tests, passed tests through `tests/test_auth.py`, then printed `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state` and produced no further pytest output before `timeout` exited `124`. |

The required verbose full-suite command timed out, so optional bounded
diagnostics were run to isolate the stalled area.

## Optional Diagnostic Evidence

| Command | Timeout | Exit | Result | Evidence |
|---|---:|---:|---|---|
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 180s .venv/bin/pytest tests/test_coach_first_ui.py -vv -ra --durations=20 -p no:cacheprovider` | `180s` | `124` | `TIMEOUT` | Collected 8 tests and hung at `test_coach_page_renders_for_authenticated_owner_with_empty_state`, the first test in the file. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 90s .venv/bin/pytest tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state -vv -s --setup-show -p no:cacheprovider` | `90s` | `124` | `TIMEOUT` | Setup output completed `reset_rate_limiter`, then the test call did not finish. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 90s .venv/bin/pytest tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state -vv -s --setup-show -o faulthandler_timeout=30 -p no:cacheprovider` | `90s` | `124` | `TIMEOUT WITH STACK` | Faulthandler showed the pytest thread waiting in `concurrent.futures._base.result`, called from AnyIO `run_sync_from_thread`, then `starlette.testclient.py` line 696 in `__enter__`, then `tests/test_coach_first_ui.py` line 51. The `asyncio-portal-` thread was in `selectors.py` `select` under the asyncio event loop. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 60s .venv/bin/pytest tests/test_web_smoke.py::test_health_endpoint -vv -ra --durations=10 -p no:cacheprovider` | `60s` | `124` | `TIMEOUT` | Collected 1 test and hung before `test_health_endpoint` completed. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 70s .venv/bin/pytest tests/test_web_smoke.py::test_health_endpoint -vv -s --setup-show -o faulthandler_timeout=25 -p no:cacheprovider` | `70s` | `124` | `TIMEOUT WITH STACK` | Same pattern: setup completed `reset_rate_limiter`; faulthandler showed pytest waiting in AnyIO from `starlette.testclient.py` line 696 in `__enter__`, then `tests/test_web_smoke.py` line 19. |

Read-only process snapshots attempted during the full-suite stall could not see
the running pytest from a separate tool call because commands run in isolated
sandbox process namespaces. That limitation does not weaken the pytest
faulthandler stack evidence captured inside the stuck pytest process.

## Diagnosis

The best-supported diagnosis is a TestClient/AnyIO portal startup stall in the
current test environment.

Evidence supporting that diagnosis:

- `--collect-only` completed quickly, so collection is not stalled.
- The full suite reached the first coach-first UI test, then stopped producing
  output until the external timeout killed it.
- The coach-first UI file alone also stalled on its first test.
- The exact coach-first UI test completed fixture setup and then stalled in the
  test call phase.
- Faulthandler placed the pytest thread in `starlette.testclient.TestClient.__enter__`
  waiting for AnyIO portal startup, not inside an assertion or coach route
  response check.
- An unrelated health endpoint test showed the same stack in
  `TestClient.__enter__`, making the likely area Starlette/FastAPI TestClient
  startup or application lifespan interaction rather than the coach page itself.

What this does not prove:

- It does not prove whether the underlying cause is app lifespan behavior,
  dependency version compatibility, event-loop/AnyIO behavior under Python
  3.14, sandbox/runtime interaction or a local test fixture pattern.
- It does not prove a product runtime bug.
- It does not authorize dependency changes, code changes, fixture rewrites or
  gate-contract changes.

## Readiness State

- H1 final readiness remains failed: `YES`.
- H2 remains blocked pending a future passing H1 rerun, acceptance and separate
  authorization: `YES`.
- WP-018 restart remains blocked pending a future passing H1 rerun, acceptance
  and separate authorization: `YES`.
- Major CS2 work remains blocked pending a future passing H1 rerun, acceptance
  and separate authorization: `YES`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK` was not set to `YES`.

PASS_WITH_WARNINGS for this diagnostic task means the likely stalled area was
identified with evidence. It does not mean H1 final readiness passed.

## Files Changed

- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md`

No product code, tests, scripts, config, status files, risk registers, PM
workspace files or deploy/service files were edited.

## Docs Update Checklist

| Checklist item | Status | Reason |
|---|---|---|
| Hot/current status docs | `checked; no update required` | Task card forbids status updates; H1 remains failed. |
| WP registry/status/handoff docs | `checked; no update required` | No readiness unlock, no H2 run and no WP-018 restart occurred. |
| Readiness gate docs | `checked; no update required` | Reviewed only; edits were outside scope. |
| Risk register | `checked; no update required` | Not read or edited; risk-register mutation was outside scope. |
| Documentation Steward | `checked; no update required` | Scoped report-only diagnostic task. |

## Safety Declarations

Forbidden actions detected: `false`.

- Implementation changed: `NO`.
- Product code/tests/scripts/config changed: `NO`.
- Docs/status/risk-register edits made except this report: `NO`.
- Production DB mutation: `NO`.
- Production DB copy: `NO`.
- Schema mutation, migration artifact edit, startup schema behavior change or
  migration-engine adoption: `NO`.
- Production DB SHA observed read-only through `project_gate.py preflight`:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Live Steam/Valve import: `NO`.
- Parser job, evaluator job or manual evaluator job: `NO`.
- Demo download, decompression, raw-demo move/delete/compression or upload
  operation: `NO`.
- Deploy/service/nginx/systemd change or restart: `NO`.
- Package installation: `NO`.
- Secrets printed in this report: `NO`.
- `git add`, commit or push: `NO`.
- H2 run: `NO`.
- WP-018 restarted: `NO`.
- Major CS2 work unlocked: `NO`.

## Blockers

No blocker prevented completing this diagnostic report.

The H1 readiness gate remains blocked because the required full-suite pytest
diagnostic command timed out. Completion of a future fix or gate rerun would
require a separately scoped task.

## Discovery Result

```yaml
discovery_result:
  completeness_estimate: "High for identifying the stalled test area; medium for root cause because code/dependency fixes were outside diagnostic scope."
  missing_items_found: true
  followup_required: true
  followup_tasks_recommended:
    - proposed_id: "FH-124R-02B"
      title: "Repair TestClient AnyIO portal startup hang"
      reason: "Bounded diagnostics isolate the recurring full-suite timeout to Starlette/FastAPI TestClient.__enter__ waiting on AnyIO portal startup, reproduced by both a coach UI test and a health endpoint smoke test."
      risk: "P1"
      suggested_scope: "code/tests"
      needs_user_decision: false
    - proposed_id: "FH-124R-02C"
      title: "Add faulthandler visibility to H1 full-suite gate"
      reason: "The timeout is otherwise low-observability; pytest faulthandler_timeout produced actionable stacks without reducing test coverage."
      risk: "P2"
      suggested_scope: "tests"
      needs_user_decision: true
```

## Machine Summary

```text
EXECUTOR_VERDICT=PASS_WITH_WARNINGS
EXECUTOR_REPORT_PATH=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md
FORBIDDEN_ACTIONS_DETECTED=false
NEEDS_USER=false
```
