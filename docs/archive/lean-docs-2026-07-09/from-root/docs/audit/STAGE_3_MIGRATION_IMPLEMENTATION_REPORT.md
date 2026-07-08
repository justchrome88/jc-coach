# Stage 3 Migration Discipline Implementation Report

Дата: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

## Migration Approach Chosen

Выбран **Option B — migration discipline scaffold без применения Alembic**.

Причина: Alembic не установлен в текущей `.venv` и не указан в `pyproject.toml`. Stage 3 не должен неконтролируемо менять dependency management или production DB. Вместо этого добавлены policy, inventory, safe copy tooling и tests.

## Production DB Touched

No mutation. Production DB использовалась только для read-only SHA/status checks.

## DB SHA Before/After

Before:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

After:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

## Files Changed

- `scripts/migration_status.sh`
- `scripts/migration_check_on_copy.sh`
- `tests/test_migrations.py`
- `docs/MIGRATIONS.md`
- `docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md`
- `docs/audit/STAGE_3_MIGRATION_IMPLEMENTATION_REPORT.md`
- `docs/PROJECT_CONTROL.md`
- `docs/CURRENT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/ROADMAP.md`
- `docs/BACKUP_RESTORE.md`
- `docs/TESTING.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/CHANGELOG.md`

## Tests Added

- Test env rejects production DB URL for migration work.
- `migration_status.sh` reads a temp DB without mutation.
- `migration_check_on_copy.sh` runs on a copied DB and keeps source unchanged.
- Copy check refuses source DB as target DB.
- Migration scripts pass `bash -n`.

## Safe Checks Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_migrations.py -q
```

Result: `6 passed`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `106 passed, 1 warning`.

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`.

```bash
git diff --check
```

Result: passed, no output.

```bash
sha256sum data/cs2_coach.db
```

Result: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`.

```bash
bash -n scripts/migration_status.sh
bash -n scripts/migration_check_on_copy.sh
```

Result: both passed.

```bash
PYTHON=.venv/bin/python scripts/migration_status.sh
PYTHON=.venv/bin/python SOURCE_DB=data/cs2_coach.db TARGET_DB=/tmp/jc-coach-stage3-migration-check.db scripts/migration_check_on_copy.sh
```

Result: status reported integrity `ok`; copy-check result `ok`; source SHA unchanged.

## Remaining Risks

- Alembic baseline is not implemented yet.
- Startup `create_all()` and `_upgrade_sqlite_schema()` remain legacy compatibility behavior.
- There is no migration revision ledger in production DB.
- Future schema stages must not add new fields through `_upgrade_sqlite_schema()`.

## Can Proceed To Stage 3 Review-Only

yes, if final safe checks pass and production DB SHA remains unchanged.
