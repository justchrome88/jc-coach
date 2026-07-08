# FH-035 Block New Schema Behavior Inside Startup Helper Report

Date: 2026-07-07

## Result

`BLOCKED`

The scoped implementation was added as a focused test-only guard, but the task
cannot be reported as `PASS` because the required local quality gate stalled and
was interrupted after no new output appeared for several polling intervals.

## Scope Performed

- Inspected `app/db/session.py::init_db()` and `_upgrade_sqlite_schema()`.
- Preserved existing startup behavior; no runtime helper code was changed.
- Added a focused regression guard in `tests/test_migrations.py` that parses
  `_upgrade_sqlite_schema()` and compares startup schema mutation SQL against
  the accepted legacy allowlist.
- Did not update `docs/MIGRATIONS.md` because it already states that new schema
  changes must not be added to `_upgrade_sqlite_schema()`.
- Context manifest note: the generated manifest task metadata still named
  accepted `FH-034`; the explicit FH-035 task card was treated as controlling.

## Files Changed

- `tests/test_migrations.py`
  - Added `LEGACY_STARTUP_SCHEMA_SQL`.
  - Added `_startup_schema_mutation_sql()`.
  - Added `test_startup_schema_helper_only_contains_accepted_legacy_sql()`.

## Acceptance Evidence

- Existing startup schema compatibility behavior remains unchanged:
  - `app/db/session.py` was inspected but not modified.
- No new schema behavior was added:
  - No new `ALTER TABLE`, `CREATE TABLE`, SQLAlchemy model/schema, migration,
    baseline artifact, copied-DB behavior or production DB behavior was added.
- Future startup helper schema mutation additions are blocked:
  - `tests/test_migrations.py::test_startup_schema_helper_only_contains_accepted_legacy_sql`
    fails if `_upgrade_sqlite_schema()` gains additional `ALTER TABLE` or
    `CREATE TABLE` string constants outside the accepted legacy allowlist.

## Checks

Initial required status before work:

```text
git status --short
<empty>
```

Context7 / external docs lookup:

```text
Context7 library: /pytest-dev/pytest
Evidence used: pytest supports standard Python assert statements with detailed
assertion introspection for simple test expectations.
```

Focused pytest:

```text
$ .venv/bin/pytest tests/test_migrations.py
collected 12 items
tests/test_migrations.py ............                                    [100%]
12 passed in 2.16s
```

Required local quality gate:

```text
$ .venv/bin/python scripts/local_quality_gate.py
LOCAL_QUALITY_GATE_ROOT=/opt/jc-coach

## project gate preflight
$ .venv/bin/python scripts/project_gate.py preflight
...
## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db

RESULT: PASS

## project gate changed
$ .venv/bin/python scripts/project_gate.py changed
## changed/untracked files
 M tests/test_migrations.py

## activated guardians
PM_ORCHESTRATOR
TEST_GUARDIAN

RESULT: PASS

## project gate required checks
$ .venv/bin/python scripts/project_gate.py required-checks
...
RESULT: PASS

## full safe pytest
$ APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
.....................................
```

After the last visible pytest progress line above, the gate produced no further
output for several polling intervals. A process check did not show an active
`local_quality_gate.py`, `pytest`, `project_gate.py` or `ruff` process in the
visible process table, while the tool session still reported running. The gate
was interrupted with Ctrl-C and exited `130`. Per the task card, this is
reported as `BLOCKED`; no weaker substitute gate is claimed.

Diff whitespace check:

```text
$ git diff --check
<empty>
```

Final status:

```text
$ git status --short
 M tests/test_migrations.py
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-035_block-new-schema-behavior-inside-startup-helper_report.md
```

## Safety Declarations

- No production DB mutation was authorized or performed.
- No production DB schema/data command was run. The only production DB evidence
  observed was the required local quality gate preflight read-only SHA output:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- No SQLAlchemy model, schema artifact, migration artifact, baseline artifact,
  copied DB or production DB state was changed.
- No live Steam/Valve import, parser job, evaluator job, manual evaluator,
  package install, service/deploy change, commit or push was performed.
- No `git add` was run.
- Forbidden actions detected: `false`.

## Blockers

- Required command `.venv/bin/python scripts/local_quality_gate.py` did not
  complete and was interrupted after apparent stall. This prevents a `PASS`
  verdict for FH-035.

## Next WP

- Re-run FH-035 verification from the current partial implementation state, or
  investigate why `scripts/local_quality_gate.py` stalled during the full safe
  pytest segment before accepting the guard.
