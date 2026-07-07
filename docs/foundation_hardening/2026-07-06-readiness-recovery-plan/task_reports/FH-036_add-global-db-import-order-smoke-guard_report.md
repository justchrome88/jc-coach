# FH-036 Add Global DB Import-Order Smoke Guard - Executor Report

Date: 2026-07-07

## Result

`FAIL`

The scoped test-only implementation was completed, and the focused smoke check
passed. The task cannot claim `PASS` because the required aggregate check,
`.venv/bin/python scripts/local_quality_gate.py`, stalled during the full safe
pytest phase and was interrupted with exit code `130`.

## Scope Completed

Added `tests/test_db_import_order.py`.

The new guard starts fresh Python subprocesses with `APP_ENV=test`, per-case
temporary SQLite `DATABASE_URL` values under pytest `tmp_path`, and test-only
runtime directories. Each subprocess imports DB/config/model modules in a
different order, calls `init_db()` against the temp database only, and asserts
that SQLAlchemy metadata tables are created in that temp database.

Covered import orders:

- `app.config`, `app.db.session`, `app.db.models`
- `app.config`, `app.db.models`, `app.db.session`
- `app.db.models`, `app.db.session`, `app.config`

## Files Changed

- `tests/test_db_import_order.py` - new focused import-order smoke guard.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-036_add-global-db-import-order-smoke-guard_report.md` - this report.

## Evidence

Initial `git status --short` before work:

```text
(clean)
```

Context used:

- Read task card:
  `/opt/jc-coach-pm/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_cards/2026-07-07_FH-036_task-card.md`
- Read context manifest:
  `/opt/jc-coach-pm/indexes/current_context_manifest.json`
- Read Hot context from manifest:
  `/opt/jc-coach/AGENTS.md`,
  `/opt/jc-coach-pm/AGENTS.md`,
  `/opt/jc-coach/docs/CURRENT_STATUS.md`,
  `/opt/jc-coach/docs/project_management/WP_REGISTRY.md`
- Read Warm workflow context only after the aggregate gate stalled, to apply
  verdict rules:
  `/opt/jc-coach/docs/project_management/AGENT_WORKFLOW.md`

External docs lookup:

- Context7 SQLAlchemy docs used for current `create_engine`, sessionmaker and
  metadata `create_all()` behavior.
- Context7 pytest docs used for current `tmp_path` and environment isolation
  fixture behavior.

Focused required check:

```text
$ .venv/bin/pytest tests/test_db_import_order.py -q
...                                                                      [100%]
3 passed in 0.80s
```

Required aggregate check:

```text
$ .venv/bin/python scripts/local_quality_gate.py
LOCAL_QUALITY_GATE_ROOT=/opt/jc-coach

## project gate preflight
...
RESULT: PASS

## project gate changed
...
RESULT: PASS

## project gate required checks
...
RESULT: PASS

## full safe pytest
$ APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
.....................................
```

The command produced no further output for several minutes after the displayed
pytest dots and was interrupted manually. The PTY exited with code `130`. No
final `LOCAL_QUALITY_GATE=PASS` or `LOCAL_QUALITY_GATE=FAIL` line was emitted.
Per `AGENT_WORKFLOW.md`, `PASS` is forbidden when a required check is stalled
or interrupted.

Additional safe checks run after the stalled aggregate gate:

```text
$ .venv/bin/ruff check tests/test_db_import_order.py --no-cache
All checks passed!
```

```text
$ git diff --check
(no output; exit 0)
```

```text
$ .venv/bin/python scripts/project_gate.py postflight
## changed/untracked files
?? tests/test_db_import_order.py

## activated guardians
IMPORT_GUARDIAN
PM_ORCHESTRATOR
TEST_GUARDIAN

## required-check summary
code/test/script change: yes
activated guardians: IMPORT_GUARDIAN, PM_ORCHESTRATOR, TEST_GUARDIAN

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Final `git status --short` before report completion:

```text
?? tests/test_db_import_order.py
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-036_add-global-db-import-order-smoke-guard_report.md
```

## Safety Declarations

- Production DB mutation: no.
- Production DB copy: no.
- Production DB dependency in the new guard: no.
- Production DB read evidence: `project_gate.py` preflight/postflight read the
  SHA only:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- New smoke test DB state: temp SQLite files under pytest `tmp_path` only.
- Schema/runtime startup behavior changed: no.
- SQLAlchemy model definitions changed: no.
- Schema baseline artifacts, migration scripts or copied-DB workflow changed:
  no.
- Live Steam/Valve import run: no.
- Parser jobs run: no.
- Evaluator/manual evaluator jobs run: no.
- Service/deploy config changed: no.
- Package installation: no.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` changed: no.
- `git add`, commit or push run: no.

Forbidden actions detected: false.

## Docs Update Checklist

- Hot/current status docs: checked; no update required. This task added a test
  guard and did not complete with a green aggregate gate.
- WP registry/status/handoff docs: checked; no update required by this failed
  implementation attempt.
- Navigation docs: not applicable; no canonical/navigation doc was created.
- Task-relevant domain docs: checked; no update required. The change is a
  focused test guard.
- Documentation Steward: closure checklist completed in this report; no broader
  docs currency review required.
- Deferred docs follow-up: none.

## Token / Context Metrics

- PM_CREATE tokens: UNKNOWN.
- EXECUTOR tokens: UNKNOWN.
- PM_REVIEW tokens: UNKNOWN.
- Total cycle tokens: UNKNOWN.
- Task verdict: `FAIL`.
- Quality verdict: `FAIL` because required local quality gate stalled and was
  interrupted.
- Broad reads avoided: Cold context was not read; Warm context was limited to
  `AGENT_WORKFLOW.md` only after it became needed for verdict rules.
- Context manifest used: true.

## Blockers And Warnings

- Blocker: required local quality gate did not complete. It stalled during full
  safe pytest and was interrupted with exit code `130`.
- Warning: the focused guard itself passed, but it is not sufficient for `PASS`
  under the task card because the aggregate gate is mandatory.

## Next WP

PM review should decide whether to rerun FH-036 after the known full-suite
pytest stall is fixed/accepted, or create a focused follow-up to diagnose the
full-suite stall before retrying this task's aggregate gate.
