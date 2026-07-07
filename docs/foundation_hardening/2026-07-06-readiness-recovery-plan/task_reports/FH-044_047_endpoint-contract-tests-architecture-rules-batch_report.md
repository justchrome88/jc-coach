# FH-044/FH-047 Endpoint Contract Tests And Architecture Rules Batch Report

Date: 2026-07-07

Task card:
`/opt/jc-coach-pm/outbox/2026-07-07_FH-047_batch_FH-044_047_task-card.md`

## Verdicts

- FH-044 verdict: `PASS_WITH_WARNINGS`
- FH-047 verdict: `PASS`
- Batch verdict: `PASS_WITH_WARNINGS`

FH-044 added a focused endpoint contract test file, and its focused pytest run
passes. The original mandatory full-suite/local quality gate checks timed out,
but targeted recovery reran the required local quality gate successfully on the
same task output. FH-044 is accepted with warnings because the tests avoid live
ASGI/TestClient dispatch and use route inventory plus direct endpoint
serialization/persistence checks against the isolated test DB.

FH-047 passed: the allowed architecture/API/testing docs now include concise
rules for future agents changing routes, services, DB/session/model code,
imports/parsers/evaluators and tests.

The batch is accepted with warnings because recovery gate evidence resolved the
original check timeout, while the known live ASGI/TestClient dispatch stall
remains outside this task's allowed product/runtime scope.

## Changes Made

- Added `tests/test_endpoint_contracts.py`.
  - Locks critical route/method inventory for `/health`, `/api/matches`,
    `/api/coach/ai/result` and `/api/coach/ai/result/latest`.
  - Locks public health serialization.
  - Locks representative API read serialization against the isolated test DB.
  - Locks representative AI-result mutation serialization and 404 behavior
    against the isolated test DB.
- Updated `docs/ARCHITECTURE.md`.
  - Added safe architecture rules for endpoint, service, DB/schema,
    import/parser/evaluator, artifact and evidence/caveat changes.
- Updated `docs/API_CONTRACTS.md`.
  - Added endpoint contract test requirements for future route/API changes.
- Updated `docs/TESTING.md`.
  - Added endpoint contract test rules and explicit non-coverage examples.

No product code, route handlers, services, DB models, runtime config,
service/deploy config, package/dependency state, generated app reports or
control-plane governance files were changed.

## External Documentation

Context7 MCP was used for current dependency/API behavior:

- FastAPI docs: `TestClient` request/assertion pattern and async testing notes.
- HTTPX docs: `ASGITransport` and `AsyncClient` ASGI app testing pattern.

The final tests do not use live ASGI dispatch because both `TestClient` and
HTTPX ASGI dispatch timed out in this repository environment before the task
could safely change runtime/middleware code. That runtime issue is outside this
Task Card scope.

## Evidence

Initial required status:

```text
git status --short
(no output)
```

Project gate preflight:

```text
.venv/bin/python scripts/project_gate.py preflight
RESULT: PASS
production DB SHA observed read-only:
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33
```

Focused checks:

```text
APP_ENV=test .venv/bin/pytest tests/test_endpoint_contracts.py -q
5 passed in 0.20s

.venv/bin/ruff check tests/test_endpoint_contracts.py --no-cache
All checks passed!
```

Required project checks:

```text
.venv/bin/python scripts/project_gate.py changed
RESULT: PASS
activated guardians: DOCUMENTATION_STEWARD, PM_ORCHESTRATOR, TEST_GUARDIAN

.venv/bin/python scripts/project_gate.py required-checks
RESULT: PASS
mandatory checks include full safe pytest and full Ruff.

git diff --check
RESULT: PASS

.venv/bin/ruff check . --no-cache
All checks passed!

.venv/bin/python scripts/project_gate.py postflight
RESULT: PASS
production DB SHA observed read-only:
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33
```

Original timed-out mandatory checks:

```text
env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 180s \
  .venv/bin/pytest tests -q -p no:cacheprovider
Output before timeout: .....................................
Exit code: 124

timeout 240s .venv/bin/python scripts/local_quality_gate.py
Reached full safe pytest step and timed out after:
.....................................
Exit code: 124
```

Recovery/final gate evidence from 2026-07-08:

```text
timeout 240s .venv/bin/python scripts/local_quality_gate.py
RESULT: PASS
full safe pytest: 233 passed, 1 warning in 11.04s
ruff: All checks passed!
git diff --check: PASS
project_gate.py preflight: PASS
project_gate.py changed: PASS
project_gate.py required-checks: PASS
project_gate.py postflight: PASS
LOCAL_QUALITY_GATE=PASS
production DB SHA observed read-only:
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33

APP_ENV=test .venv/bin/pytest tests/test_endpoint_contracts.py -q
5 passed in 0.21s

.venv/bin/ruff check tests/test_endpoint_contracts.py --no-cache
All checks passed!

git -C /opt/jc-coach diff --check
PASS

git -C /opt/jc-coach-pm diff --check
PASS
```

Additional diagnostic evidence:

```text
env APP_ENV=test timeout 90s \
  .venv/bin/pytest tests/test_web_smoke.py::test_health_endpoint -vv -s
Timed out while running existing test_web_smoke health TestClient test.

env APP_ENV=test timeout 90s \
  .venv/bin/pytest tests/test_endpoint_contracts.py -vv -s
Timed out on the first live ASGI/TestClient health request before final test
rewrite avoided live dispatch.
```

## Safety Declarations

- Production DB mutation: no.
- Production DB read-only SHA evidence: yes, via `project_gate.py preflight`
  and `project_gate.py postflight`.
- Production DB touched for writes: no.
- Schema/model/startup/migration/baseline/copy changes: no.
- Live Steam/Valve import run: no.
- Parser jobs run: no.
- Evaluator/manual evaluator jobs run: no.
- Service start/restart or deploy/runtime config change: no.
- Generated persistent app reports: no production app reports; test mutation
  wrote only to pytest-isolated temp DB/artifact configuration.
- Raw demos moved/deleted/compressed: no.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` changed: no.
- `git add`, commit or push: no.
- Forbidden actions detected: no.

## Scope Review

Allowed files changed:

- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACTS.md`
- `docs/TESTING.md`
- `tests/test_endpoint_contracts.py`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-044_047_endpoint-contract-tests-architecture-rules-batch_report.md`

The changes are tests-only plus governance/documentation-only. The report file
is the Task Card's allowed report path.

## Warnings

- Original mandatory full safe pytest timed out after 180 seconds.
- Original mandatory `scripts/local_quality_gate.py` timed out after 240
  seconds at the full safe pytest step.
- Recovery rerun of `scripts/local_quality_gate.py` passed and included full
  safe pytest, Ruff, git diff, project gate and `LOCAL_QUALITY_GATE=PASS`
  evidence.
- Existing live ASGI dispatch through FastAPI `TestClient` timed out even for
  `tests/test_web_smoke.py::test_health_endpoint`. Because product/runtime
  changes were forbidden, FH-044 contract tests were implemented as route
  inventory plus direct endpoint serialization tests rather than live ASGI
  request tests.

## Next WP

Recommended follow-up:

- Investigate and repair the existing FastAPI/TestClient or ASGI dispatch
  stall in a task explicitly scoped for route test harness/runtime middleware
  diagnosis. After that, upgrade `tests/test_endpoint_contracts.py` to verify
  live status/auth/owner/CSRF behavior through the HTTP/ASGI request path.
