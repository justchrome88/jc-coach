> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/BACKUP_RESTORE.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Backup And Restore

Last updated: 2026-07-07.

## Current Status

JC Coach has a controlled local/VPS backup and restore verification process.
It is a safety foundation for schema-risk and DB-risk work, not a full
production disaster-recovery program and not final readiness evidence.

Backup/restore hardening does not authorize DB mutation, schema changes,
parser/import/evaluator jobs, service changes, migration support or Alembic
adoption. Those actions require explicit Task Card scope and the safety
evidence required by `AGENTS.md`.

## What Is Backed Up

Default backup command:

```bash
scripts/backup_runtime.sh
```

It creates files under `backups/`:

- `cs2_coach_YYYYMMDD_HHMMSS.db` - SQLite backup of `data/cs2_coach.db`.
- `runtime_artifacts_YYYYMMDD_HHMMSS.tar.gz` - selected runtime artifact
  directories.
- `backup_YYYYMMDD_HHMMSS.manifest.txt` - restore/check metadata.

Included artifact directories:

- `data/reports`
- `data/uploads`
- `data/incoming_demos`
- `data/ai_handoffs`

Excluded by default:

- `.env`
- `data/steam_bot_credentials`
- `*.dem`
- `*.dem.bz2`

Raw demos are intentionally excluded from the default artifact archive because
retention/deletion policy is not closed and local demos can be large/sensitive.
The database backup remains mandatory for authorized production DB mutation.

## Backup Command

```bash
scripts/backup_runtime.sh
```

Optional environment variables:

```bash
BACKUP_DIR=/secure/path/backups scripts/backup_runtime.sh
DB_PATH=/path/to/cs2_coach.db scripts/backup_runtime.sh
```

Backups are runtime artifacts. They must not be committed.

## Restore Verification On A Copy

Restore verification must target a copy, never `data/cs2_coach.db`:

```bash
scripts/restore_runtime.sh \
  --db-backup backups/cs2_coach_YYYYMMDD_HHMMSS.db \
  --target-db /tmp/jc-coach-restore-test.db \
  --verify-only
```

Expected output:

```text
RESTORE_VERIFY_OK=/tmp/jc-coach-restore-test.db
```

If `sqlite3` is available, the script runs `PRAGMA integrity_check;` on the
restored copy.

Restore verification on a copy is copied-DB work. It does not authorize
production DB mutation, schema artifact changes, migration/baseline edits or
startup schema behavior changes.

## Production Restore Guard

The restore script refuses to overwrite `data/cs2_coach.db` unless the operator
explicitly sets:

```bash
ALLOW_PRODUCTION_RESTORE=1
```

Production restore is production DB mutation. It requires explicit
operator/WP authorization, backup evidence and before/after SHA evidence for
`data/cs2_coach.db`.

Production restore example, only after the operator has stopped the app,
accepted data replacement and authorized the production mutation:

```bash
ALLOW_PRODUCTION_RESTORE=1 scripts/restore_runtime.sh \
  --db-backup backups/cs2_coach_YYYYMMDD_HHMMSS.db \
  --target-db data/cs2_coach.db
```

Artifact restore into the repository root has the same guard.

## Work Class Boundaries

Docs-only work:

- may update approved documentation files;
- must not inspect or mutate production DB unless explicitly scoped;
- may declare no production DB touch when no DB/schema/import/parser/evaluator
  action was performed.

Read-only production DB inspection:

- must be explicitly scoped when the task depends on current DB state;
- must record the observed `sha256sum data/cs2_coach.db`;
- must record the read-only command or gate evidence used;
- does not authorize copied-DB experiments, restore, migration apply or DB
  mutation.

Copied-DB work:

- must use a copy target outside `data/cs2_coach.db`;
- may include restore verification, schema copy checks or temporary test DB
  inspection when explicitly scoped;
- must not write to the production DB;
- does not authorize schema artifacts, runtime startup behavior changes or
  production mutation.

Authorized production DB mutation:

- requires explicit operator/WP authorization;
- requires a backup before mutation;
- requires before and after `sha256sum data/cs2_coach.db`;
- requires task-specific verification after mutation;
- must report the exact command or app-service action used.

## Required Before Schema-Risk Or DB-Risk Work

For DB/schema-risk tasks that do not touch `data/cs2_coach.db`, report an
explicit no-production-DB-touch declaration and state which DB/schema scope was
intentionally avoided.

Before any authorized production DB mutation:

1. Run `scripts/backup_runtime.sh`.
2. Verify restore on a copy with `scripts/restore_runtime.sh --verify-only`.
3. Record `sha256sum data/cs2_coach.db` before the mutation.
4. Write the exact SQL, script or app-service repair command in the work log
   before running it.
5. Run only the explicitly approved mutation.
6. Record `sha256sum data/cs2_coach.db` after the mutation.
7. Run task-specific verification on the result.

Before any future schema change or migration apply:

1. Run `scripts/backup_runtime.sh`.
2. Verify restore on a copy with `scripts/restore_runtime.sh --verify-only`.
3. Run `scripts/migration_status.sh` and record source DB SHA.
4. Run `scripts/migration_check_on_copy.sh` against a copy.
5. Run the FH-030 schema baseline gate or accepted successor.
6. Do not apply to `data/cs2_coach.db` without explicit operator approval.

## Git Rules

- `backups/` is ignored by git.
- Do not commit `.env`, `data/*.db`, raw demos, generated reports, handoff
  files, Steam bot credentials or refresh tokens.
- Do not commit `data/cs2_coach.db`, `data/manual_backups`, `data/uploads`,
  `.dem` files, `.dem.bz2` files or `__pycache__`.
- Backup files are runtime artifacts, not source files.

## Current Known Limits

- This process is local/VPS backup and restore verification, not hosted CI and
  not branch protection.
- It does not resolve the known full-suite pytest stall.
- It does not prove final foundation readiness.
- It does not establish raw demo retention, deletion or storage migration
  policy.
- It does not add migration support or adopt Alembic.
