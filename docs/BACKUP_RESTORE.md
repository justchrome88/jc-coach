# Backup And Restore

Last updated: 2026-07-03.

## Current Status

Stage 0 backup/restore process exists for controlled local/VPS hardening work.

This is not yet a full production disaster-recovery program. It is the minimum safe foundation before Security P0, ownership, migrations or other risky changes.

## What Is Backed Up

Default backup command:

```bash
scripts/backup_runtime.sh
```

It creates files under `backups/`:

- `cs2_coach_YYYYMMDD_HHMMSS.db` — SQLite backup of `data/cs2_coach.db`.
- `runtime_artifacts_YYYYMMDD_HHMMSS.tar.gz` — selected runtime artifact directories.
- `backup_YYYYMMDD_HHMMSS.manifest.txt` — restore/check metadata.

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

Raw demos are intentionally excluded from the default artifact archive because retention/deletion policy is not closed yet and local demos can be large/sensitive. The database backup remains mandatory.

## Backup Command

```bash
scripts/backup_runtime.sh
```

Optional environment variables:

```bash
BACKUP_DIR=/secure/path/backups scripts/backup_runtime.sh
DB_PATH=/path/to/cs2_coach.db scripts/backup_runtime.sh
```

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

If `sqlite3` is available, the script runs `PRAGMA integrity_check;` on the restored copy.

## Production Restore Guard

The restore script refuses to overwrite `data/cs2_coach.db` unless the operator explicitly sets:

```bash
ALLOW_PRODUCTION_RESTORE=1
```

Production restore example, only after the operator has stopped the app and accepted data replacement:

```bash
ALLOW_PRODUCTION_RESTORE=1 scripts/restore_runtime.sh \
  --db-backup backups/cs2_coach_YYYYMMDD_HHMMSS.db \
  --target-db data/cs2_coach.db
```

Artifact restore into the repository root has the same guard.

## Git Rules

- `backups/` is ignored by git.
- Do not commit `.env`, `data/*.db`, raw demos, generated reports, handoff files, Steam bot credentials or refresh tokens.
- Backup files are runtime artifacts, not source files.

## Required Before Risky Work

Before Security P0, ownership, migrations or parser/Steam hardening:

1. Run `scripts/backup_runtime.sh`.
2. Run restore verification against `/tmp`.
3. Confirm the source DB file timestamp/hash did not change during verification.
4. Record the backup filename in the work summary.

## Required Before Schema Changes

Before any future schema change or migration apply:

1. Run `scripts/backup_runtime.sh`.
2. Verify restore on a copy with `scripts/restore_runtime.sh --verify-only`.
3. Run `scripts/migration_status.sh` and record source DB SHA.
4. Run `scripts/migration_check_on_copy.sh` against a copy.
5. Do not apply to `data/cs2_coach.db` without explicit operator approval.
