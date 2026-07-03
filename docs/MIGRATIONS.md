# Migrations

Last updated: 2026-07-03.

## Current Policy

Stage 3 вводит migration discipline scaffold без применения Alembic к production DB.

Выбранный подход: **Option B — safe migration discipline scaffold**.

Причина: Alembic не установлен в текущей `.venv` и не указан в `pyproject.toml`. Добавлять новую dependency и сразу включать полноценный migration engine без отдельного dependency review сейчас шире Stage 3 safety scope.

## Non-Negotiable Rules

- Production DB `data/cs2_coach.db` нельзя менять без explicit backup and approval.
- Любая schema change сначала проверяется на копии DB.
- Новые изменения схемы нельзя добавлять в startup helper `_upgrade_sqlite_schema()`.
- Existing startup `create_all()` и `_upgrade_sqlite_schema()` остаются legacy compatibility path до отдельной замены.
- Tests должны идти только через `APP_ENV=test` и temp DB.
- Import, Steam и parser production jobs не являются частью migration validation.

## Current Legacy Startup Behavior

`app/db/session.py::init_db()` сейчас делает:

```text
Base.metadata.create_all(bind=engine)
_upgrade_sqlite_schema()
```

`_upgrade_sqlite_schema()` содержит legacy manual SQLite `ALTER TABLE` для старых локальных DB.

Policy after Stage 3:

- не добавлять туда новые schema changes;
- не удалять legacy helper без replacement и отдельного review;
- будущие поля/таблицы оформлять через migration-first процесс.

## Safe Commands

Read-only status for a DB:

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
- runs app `init_db()` only against target copy;
- runs SQLite integrity check on target;
- verifies source DB SHA did not change.

## Required Before Any Future Schema Change

1. Create runtime backup:

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

4. Record DB SHA before and after.

5. Only then implement schema changes through an explicit migration file/process.

## How To Inspect Current Schema

```bash
scripts/migration_status.sh
```

For deeper manual inspection:

```bash
sqlite3 data/cs2_coach.db ".schema"
```

Run manual inspection only as read-only unless the task explicitly allows DB mutation.

## Future Alembic Adoption

Preferred future direction remains Alembic-based migrations with a current schema baseline.

Before adopting Alembic:

- add Alembic to dependency management intentionally;
- create baseline revision matching current SQLAlchemy models/production schema;
- make `alembic current` safe for test/temp DB;
- require `ALLOW_PRODUCTION_MIGRATION=1` for production apply;
- keep dry-run-on-copy mandatory.

Until then, this document and the scripts are the migration discipline source of truth.
