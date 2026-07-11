# FH-030 Create Migration Baseline And Schema Gate Report

Date: 2026-07-07

Executor verdict: `PASS_WITH_WARNINGS`

## Result

Created a deterministic SQLite schema baseline and a schema gate command for
detecting unexpected schema drift before future schema work touches production
data.

The baseline is schema-only and excludes row data. It captures:

- SQLite schema objects from `sqlite_master`;
- table columns;
- foreign keys;
- non-internal indexes and indexed columns;
- `PRAGMA user_version`;
- `PRAGMA application_id`;
- a deterministic schema hash over the schema payload.

## Changed Files

- `docs/MIGRATIONS.md`
- `scripts/schema_baseline_gate.py`
- `tests/test_migrations.py`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-030_create-migration-baseline-and-schema-gate_report.md`

## Production DB Safety

- Production DB path: `data/cs2_coach.db`
- Production DB access performed: read-only SHA/schema inspection only.
- Production DB mutation: no.
- Production schema apply/migration: no.
- Backup/restore action: no.
- Import/parser/evaluator/manual evaluator jobs: no.
- Service/nginx/systemd/deploy actions: no.
- Package/dependency changes: no.
- `git add`, commit or push: no.

DB SHA before work:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA after implementation checks:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA changed: no.

## External Docs

Context7 MCP was used for current pytest guidance. Source selected:
`/pytest-dev/pytest`. The relevant guidance confirmed `tmp_path` provides an
isolated per-test `pathlib.Path` temporary directory and `monkeypatch` is the
pytest fixture for temporary test environment modifications. The implemented
tests use pytest temp paths for DB mutation paths.

## Implementation Evidence

Baseline generation output:

```text
SCHEMA_BASELINE_DB=/opt/jc-coach/data/cs2_coach.db
SCHEMA_BASELINE_OUTPUT=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json
SCHEMA_BASELINE_HASH=sha256:68a137643d87789533f4440794f97bd7313a9fea1476a98ed078361131867070
SCHEMA_BASELINE_RESULT=written
```

Schema gate match output:

```text
SCHEMA_GATE_DB=/opt/jc-coach/data/cs2_coach.db
SCHEMA_GATE_BASELINE=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json
SCHEMA_GATE_BASELINE_HASH=sha256:68a137643d87789533f4440794f97bd7313a9fea1476a98ed078361131867070
SCHEMA_GATE_CURRENT_HASH=sha256:68a137643d87789533f4440794f97bd7313a9fea1476a98ed078361131867070
SCHEMA_GATE_RESULT=match
```

Temp-DB mismatch output evidence. This command intentionally used only a `/tmp`
database and returned exit code `1`:

```text
SCHEMA_BASELINE_DB=/tmp/jc-coach-schema-gate.D2spq7/schema.db
SCHEMA_BASELINE_OUTPUT=/tmp/jc-coach-schema-gate.D2spq7/baseline.json
SCHEMA_BASELINE_HASH=sha256:60502ffc9ad2ee7fe7a708e1b1446c62b97c31c8ae125ff2e2e9f3687f96e458
SCHEMA_BASELINE_RESULT=written
SCHEMA_GATE_DB=/tmp/jc-coach-schema-gate.D2spq7/schema.db
SCHEMA_GATE_BASELINE=/tmp/jc-coach-schema-gate.D2spq7/baseline.json
SCHEMA_GATE_BASELINE_HASH=sha256:60502ffc9ad2ee7fe7a708e1b1446c62b97c31c8ae125ff2e2e9f3687f96e458
SCHEMA_GATE_CURRENT_HASH=sha256:5a9cf0f0ee73c54921a7304e994e3d0910800efd1f9c1d04fefeab9a878a81b5
SCHEMA_GATE_RESULT=mismatch
SCHEMA_GATE_DIFF_BEGIN
--- baseline_schema
+++ current_schema
@@ -4,7 +4,7 @@
   "objects": [
     {
       "name": "existing_table",
-      "sql": "CREATE TABLE existing_table (id INTEGER PRIMARY KEY, value TEXT)",
+      "sql": "CREATE TABLE existing_table (id INTEGER PRIMARY KEY, value TEXT, drift TEXT)",
       "tbl_name": "existing_table",
       "type": "table"
     }
@@ -27,6 +27,14 @@
           "notnull": 0,
           "pk": 0,
           "type": "TEXT"
+        },
+        {
+          "cid": 2,
+          "default": null,
+          "name": "drift",
+          "notnull": 0,
+          "pk": 0,
+          "type": "TEXT"
         }
       ],
       "foreign_keys": [],
SCHEMA_GATE_DIFF_END
```

## Required Checks

This Task Card explicitly authorized a narrower DB-specific PASS check set
instead of the full local quality gate because the known unrelated full-suite
pytest stall remains unresolved.

Initial `git status --short` before edits:

```text
(no output)
```

Initial project gate preflight:

```text
## task context
working_directory: /opt/jc-coach
branch: agentdev

## git status --short -uall
(no output)

## git log --oneline -12 --decorate
4eae952 (HEAD -> agentdev, origin/agentdev) FH-026 add dirty worktree stop condition
0b7db63 FH-025 require gate output evidence
a95fb3f FH-024 enforce mandatory PASS policy
5d2eb2 FH-023 accept local CI-equivalent gate
5e9686e FH-022 document required checks policy
f49b3f5 FH-021 local quality gate command
17a2b69 FH-020 done
e312385 Align workflow git policy
30f5576 FH-015 register roadmap pause state
53505d2 FH-014 mark historical docs non-current
e1a14f5 Add discovery task decomposition contract
a960b90 FH-013 add docs update checklist to reports

## governance files
AGENTS.md: present
docs/CURRENT_STATUS.md: present
docs/HANDOFF.md: present
docs/project_management/WP_REGISTRY.md: present
docs/project_management/AGENT_WORKFLOW.md: present
docs/TESTING.md: present

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Initial project gate changed:

```text
## changed/untracked files
(none)

## activated guardians
PM_ORCHESTRATOR
```

Initial project gate required-checks:

```text
## mandatory local gate expectations
- .venv/bin/python scripts/project_gate.py preflight
- .venv/bin/python scripts/project_gate.py changed
- .venv/bin/python scripts/project_gate.py required-checks
- .venv/bin/python scripts/project_gate.py postflight
- git diff --check

## required checks by activated guardian
PM_ORCHESTRATOR:
- REQUIRED: .venv/bin/python scripts/project_gate.py preflight
- REQUIRED: .venv/bin/python scripts/project_gate.py changed
- REQUIRED: .venv/bin/python scripts/project_gate.py required-checks
- REQUIRED: .venv/bin/python scripts/project_gate.py postflight
- REQUIRED: git diff --check
- REQUIRED: confirm no unauthorized git add/commit/push
- RECOMMENDED: include initial git status, changed files, guardians and final git status in report
```

Post-edit project gate changed:

```text
## changed/untracked files
 M docs/MIGRATIONS.md
 M tests/test_migrations.py
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json
?? scripts/schema_baseline_gate.py

## activated guardians
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR
TEST_GUARDIAN
```

Post-edit project gate required-checks:

```text
## mandatory local gate expectations
- .venv/bin/python scripts/project_gate.py preflight
- .venv/bin/python scripts/project_gate.py changed
- .venv/bin/python scripts/project_gate.py required-checks
- .venv/bin/python scripts/project_gate.py postflight
- git diff --check
- APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
- .venv/bin/ruff check . --no-cache

## required checks by activated guardian
DOCUMENTATION_STEWARD:
- REQUIRED: complete the report docs update checklist
- REQUIRED: confirm Hot/current status docs updated or not required
- REQUIRED: confirm navigation docs updated or not required
- RECOMMENDED: check changed docs do not weaken AGENTS.md or control-plane policy
PM_ORCHESTRATOR:
- REQUIRED: .venv/bin/python scripts/project_gate.py preflight
- REQUIRED: .venv/bin/python scripts/project_gate.py changed
- REQUIRED: .venv/bin/python scripts/project_gate.py required-checks
- REQUIRED: .venv/bin/python scripts/project_gate.py postflight
- REQUIRED: git diff --check
- REQUIRED: confirm no unauthorized git add/commit/push
- RECOMMENDED: include initial git status, changed files, guardians and final git status in report
TEST_GUARDIAN:
- REQUIRED: APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
- REQUIRED: .venv/bin/ruff check . --no-cache
- REQUIRED: git diff --check
- RECOMMENDED: run focused tests for the changed test/script surface before the full suite
```

Targeted migration/schema tests:

```text
.........                                                                [100%]
9 passed in 1.36s
```

DB-safety focused tests:

```text
.............                                                            [100%]
13 passed in 1.02s
```

Ruff on changed Python files:

```text
All checks passed!
```

Shell parse checks:

```text
bash -n scripts/migration_status.sh
(no output; exit 0)

bash -n scripts/migration_check_on_copy.sh
(no output; exit 0)
```

Final `git diff --check`:

```text
(no output; exit 0)
```

Final project gate postflight:

```text
## git diff --stat
docs/MIGRATIONS.md       | 26 ++++++++++++++++++-
 tests/test_migrations.py | 66 ++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 91 insertions(+), 1 deletion(-)

## changed/untracked files
 M docs/MIGRATIONS.md
 M tests/test_migrations.py
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-030_create-migration-baseline-and-schema-gate_report.md
?? scripts/schema_baseline_gate.py

## activated guardians
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR
TEST_GUARDIAN

## required-check summary
code/test/script change: yes
activated guardians: DOCUMENTATION_STEWARD, PM_ORCHESTRATOR, TEST_GUARDIAN

## governance files
AGENTS.md: present
docs/CURRENT_STATUS.md: present
docs/HANDOFF.md: present
docs/project_management/WP_REGISTRY.md: present
docs/project_management/AGENT_WORKFLOW.md: present
docs/TESTING.md: present

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db

## reminder
- Run safe tests with APP_ENV=test before claiming completion.
- Run runtime smoke only when explicitly authorized and report service restart yes/no.
- Report production DB touched yes/no and live jobs run yes/no.
```

Checks not run:

- Full `.venv/bin/python scripts/local_quality_gate.py`: not run because the
  Task Card explicitly authorized the narrower DB-specific PASS check set due
  to the known unrelated full-suite pytest stall.
- Full `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`:
  not run for the same Task Card authorization.
- Whole-repo Ruff: not run; Task Card required Ruff on changed Python files if
  Python files changed, and that passed.

## Documentation Steward Checklist

- Hot/current status docs: checked; no update required because FH-030 adds a
  migration safety artifact and does not change project status, roadmap pause
  state or active WP state.
- WP registry/status/handoff docs: checked; no update required because this
  foundation-hardening task does not create, promote, block or close a product
  WP in canonical registry/status docs.
- Navigation docs: checked; no update required because no new canonical
  navigation entrypoint was created; the baseline artifact is documented from
  existing `docs/MIGRATIONS.md`.
- Task-relevant domain docs: checked and updated in `docs/MIGRATIONS.md`.
- Documentation Steward: completed through this scoped checklist; no
  control-plane docs were changed.
- Deferred docs follow-up: none.

## Blockers

None.

## Warnings / Residual Risk

- This adds a SQLite schema baseline/gate scaffold only. It does not adopt
  Alembic, replace legacy startup schema behavior or authorize production
  schema mutation.
- The local full-suite pytest stall remains unresolved and was not claimed as
  fixed.

## Next WP

PM review of FH-030 output. Next task selection remains with PM/User; Executor
did not choose or start follow-up work.
