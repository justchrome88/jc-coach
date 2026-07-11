> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/MIGRATIONS.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Migrations

Last updated: 2026-07-07.

## Current Policy

JC Coach currently uses a migration discipline scaffold, not an adopted
migration engine.

Accepted state after FH-030 through FH-036:

- FH-030 added a deterministic schema baseline artifact and a read-only schema
  baseline gate.
- FH-031 defined the schema-changing approval policy.
- FH-032 added the production DB SHA evidence policy.
- FH-033 documented startup schema compatibility boundaries.
- FH-034 added a safe copied-DB schema diff/check workflow.
- FH-035 added a test-only startup helper allowlist guard.
- FH-036 added a global DB import-order smoke guard.

Alembic has not been adopted. Migration support has not been added. The
production DB has not been migrated by this hardening sequence.

## Non-Negotiable Rules

- Production DB `data/cs2_coach.db` must not be changed without explicit
  operator/WP authorization, a backup, and before/after SHA evidence.
- Schema-changing work is `approval-required` unless the active Task Card
  explicitly names the schema scope and allowed files/artifacts.
- Schema scope must distinguish read-only schema inspection, schema
  definition/code changes, startup schema behavior changes, schema baseline or
  migration artifact changes, copied-DB experiments, and production DB
  mutation.
- Authorization for one schema category does not authorize another. For
  example, read-only inspection does not authorize copied-DB work or production
  DB mutation.
- New schema changes must not be added to startup helper compatibility behavior
  unless a future Task Card explicitly scopes startup schema behavior changes.
- Existing startup `create_all()` and legacy compatibility helper behavior
  remain compatibility boundaries until a separate approved replacement.
- Tests must use `APP_ENV=test` and a temp DB.
- Import, Steam, parser and evaluator production jobs are not migration
  validation and must not be run for migration evidence unless explicitly
  authorized by a task.

## Current Startup Compatibility Boundary

`app/db/session.py::init_db()` currently performs startup DB setup for the
application. That behavior is treated as a compatibility boundary, not a place
for new unreviewed schema changes.

Current policy:

- documenting compatibility boundaries does not authorize runtime startup
  behavior changes;
- changing startup helper behavior is schema-changing work;
- future startup schema compatibility tasks must state allowed files/artifacts,
  required schema-gate evidence, rollback and compatibility expectations, and
  production DB authorization status;
- FH-030, FH-031 and FH-032 did not adopt Alembic, add migration support,
  mutate the production DB or change startup schema behavior.

FH-035 added a test-only allowlist guard for startup helper schema mutations.
That guard exists to catch unexpected helper drift in tests. It is not
authorization to add helper mutations or to treat helper mutations as the
accepted migration path.

FH-036 added a global DB import-order smoke guard. That guard exists to catch
unsafe import ordering around DB/session initialization. It is not hosted CI,
not final readiness evidence, and not a substitute for schema approval.

## Schema Baseline Gate

The current deterministic schema baseline is:

```text
app/contracts/db/current_schema_baseline.json
```

Run the schema gate directly against a DB:

```bash
.venv/bin/python scripts/schema_baseline_gate.py check \
  --db-path /tmp/jc-coach-migration-check.db \
  --baseline app/contracts/db/current_schema_baseline.json
```

The schema gate opens SQLite read-only, compares schema structure only and
excludes row data. It exits nonzero when the inspected schema differs from the
accepted baseline. The baseline includes tables, columns, foreign keys,
indexes, schema SQL objects, `PRAGMA user_version` and
`PRAGMA application_id`. During comparison, SQLite index-list ordinals are
normalized so equivalent schemas do not fail because of non-semantic
`PRAGMA index_list` ordering.

Create or refresh the baseline only under an explicit schema artifact task:

```bash
.venv/bin/python scripts/schema_baseline_gate.py write-baseline \
  --db-path data/cs2_coach.db \
  --output app/contracts/db/current_schema_baseline.json
```

Refreshing the baseline is a schema artifact change. It must not be done as an
incidental docs, code, test or startup-helper task.

## Safe Read-Only And Copied-DB Commands

Read-only status for the default DB:

```bash
scripts/migration_status.sh
```

Status for a specific DB:

```bash
DB_PATH=/tmp/cs2_coach_copy.db scripts/migration_status.sh
```

Dry-run startup schema compatibility on a copy:

```bash
scripts/migration_check_on_copy.sh
```

With explicit source/target:

```bash
SOURCE_DB=data/cs2_coach.db \
TARGET_DB=/tmp/jc-coach-migration-check.db \
scripts/migration_check_on_copy.sh
```

The copy check:

- copies source DB to target;
- runs app startup DB initialization only against the target copy;
- runs SQLite integrity check on the target;
- verifies source DB SHA did not change;
- refuses `data/cs2_coach.db` as a target path;
- runs the FH-030 schema baseline gate against the target copy;
- prints a unified schema diff when the copy differs from the accepted
  baseline.

For isolated test fixtures or temporary experiments, pass an explicit
`SCHEMA_BASELINE=/path/to/baseline.json`. Do not use that override to weaken
production review evidence.

## Required Before Future Schema-Changing Work

Future schema-changing Task Cards must state:

- which schema scope category applies;
- allowed schema files, scripts and artifacts;
- whether production DB mutation is authorized;
- required production DB backup plus before/after SHA evidence when production
  DB mutation is authorized;
- required FH-030 schema-gate or successor evidence;
- rollback and compatibility expectations, or why they do not apply.

Before any future authorized production schema mutation:

1. Run a runtime backup:

   ```bash
   scripts/backup_runtime.sh
   ```

2. Verify restore on a copy:

   ```bash
   scripts/restore_runtime.sh \
     --db-backup backups/cs2_coach_YYYYMMDD_HHMMSS.db \
     --target-db /tmp/jc-coach-restore-test.db \
     --verify-only
   ```

3. Run migration copy check:

   ```bash
   SOURCE_DB=data/cs2_coach.db \
   TARGET_DB=/tmp/jc-coach-migration-check.db \
   scripts/migration_check_on_copy.sh
   ```

4. Record `sha256sum data/cs2_coach.db` before mutation.

5. Run the schema gate and investigate unexpected drift before touching
   production data.

6. Apply only the explicitly approved schema change.

7. Record `sha256sum data/cs2_coach.db` after mutation and verify the expected
   schema state.

Copied-DB work does not authorize production DB mutation. Production DB
mutation still requires explicit authorization, backup evidence and SHA
evidence.

## How To Inspect Current Schema

```bash
scripts/migration_status.sh
```

For deeper manual inspection:

```bash
sqlite3 data/cs2_coach.db ".schema"
```

Manual production DB inspection is read-only unless the task explicitly allows
DB mutation. Read-only inspection must record the observed production DB SHA
and the read-only command/evidence used.

## Future Alembic Adoption

Preferred future direction remains Alembic-based migrations with a current
schema baseline.

Before adopting Alembic:

- add Alembic to dependency management intentionally;
- create a baseline revision matching current SQLAlchemy models and production
  schema;
- make `alembic current` safe for test/temp DB;
- require an explicit production-apply guard for production migration;
- keep dry-run-on-copy mandatory;
- preserve the production DB backup and SHA evidence policy.

Until a future approved task adopts a migration engine, this document and the
accepted hardening scripts are the migration discipline source of truth.
