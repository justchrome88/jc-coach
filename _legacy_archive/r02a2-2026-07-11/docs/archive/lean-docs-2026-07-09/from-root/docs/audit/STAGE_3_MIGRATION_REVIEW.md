# Stage 3 Migration Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 3 вводит минимальную migration discipline без изменения production DB и без изменения product behavior. Реализованы schema evolution inventory, migration policy, safe status/copy-check scripts и тесты безопасного поведения.

Статус не `PASS`, потому что выбран Option B scaffold: Alembic baseline и migration ledger ещё не внедрены. Это честно задокументировано и не блокирует Stage 4 при условии, что Stage 4 не делает schema changes.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | current schema evolution inventory exists and is accurate | PASS | `docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md` фиксирует `engine`, `init_db()`, `create_all`, `_upgrade_sqlite_schema()` и manual `ALTER` для `matches`, `coach_reports`, `users`, `coach_recommendations`. |
| 2 | migration policy documented | PASS | `docs/MIGRATIONS.md` описывает Option B, no production mutation without approval, copy-first checks and future migration-first rule. |
| 3 | safe migration tooling exists | PASS | Added `scripts/migration_status.sh` and `scripts/migration_check_on_copy.sh`. Both passed syntax and runtime checks. |
| 4 | Option B без Alembic честно обоснован | PASS | `docs/MIGRATIONS.md` and implementation report state Alembic is not installed in `.venv` and not in `pyproject.toml`; dependency change is deferred. |
| 5 | production DB SHA unchanged | PASS | SHA before and after review checks: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`. |
| 6 | backup-before-migration procedure documented | PASS | `docs/BACKUP_RESTORE.md` and `docs/MIGRATIONS.md` require backup, restore verify, status SHA and copy-check before schema changes. |
| 7 | startup `create_all`/`_upgrade_sqlite_schema` documented as legacy compatibility behavior | PASS | `docs/MIGRATIONS.md` and inventory document both as legacy compatibility paths. |
| 8 | future schema changes must not be added through startup upgrade helper | PASS | `docs/MIGRATIONS.md` explicitly forbids new schema changes in `_upgrade_sqlite_schema()`. |
| 9 | `tests/test_migrations.py` проверяет safe behavior | PASS | Tests cover production DB guard, read-only status, copy-check source unchanged, source=target refusal and shell syntax. |
| 10 | migration scripts are safe-by-default | PASS_WITH_WARNING | Scripts default to status/copy-check, not apply. `migration_status.sh` opens DB with SQLite `mode=ro`; `migration_check_on_copy.sh` copies source before `init_db()`. It still defaults source to production DB for copy-check, but target is a temp copy and source SHA is verified unchanged. |
| 11 | scripts do not mutate source DB | PASS | Copy-check records source SHA before/after and exits if changed. Review run preserved production SHA. |
| 12 | scripts refuse unsafe source=target behavior | PASS | Script compares `realpath` source and target and exits with code `3`; test covers this. |
| 13 | full safe pytest passes | PASS | `APP_ENV=test .venv/bin/pytest tests -q`: `106 passed, 1 warning`. |
| 14 | ruff passes | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 15 | git diff --check passes | PASS | `git diff --check`: passed, no output. |
| 16 | import/Steam/parser production jobs not run | PASS | Review ran only pytest/ruff/diff/SHA/shell/script checks. No production jobs were invoked. |
| 17 | no coach/recommendation/metric/parser/Steam/AI/UI behavior changes | PASS | Current diff changes docs, scripts and `tests/test_migrations.py`; no `app/` product modules changed in Stage 3. |

## Migration Approach Review

- Почему Option B принят вместо Alembic: Alembic is not installed in `.venv` and is not declared in `pyproject.toml`. Adding a new migration dependency and baseline in the same safety stage would expand scope and dependency management risk. Option B creates enforceable process and copy-check tooling without production mutation.
- Является ли отсутствие Alembic blocker before Stage 4: no, if Stage 4 does not make schema changes. It remains a warning and a blocker before any stage that needs new tables/columns or destructive schema work.
- Какие schema changes после Stage 3 запрещены без migration discipline: any new tables, columns, indexes, constraints, ownership columns, recommendation/problem snapshot tables, metric truth tables, parser fact fields, Steam job/cursor tables, AI validation tables, or changes to existing column semantics. New schema changes must not be added through `_upgrade_sqlite_schema()`.
- Можно ли Stage 4 делать без Alembic baseline: yes, only if Stage 4 is code/process-only and does not mutate schema. If Stage 4 requires schema changes, it must either adopt Alembic/baseline first or run an explicit migration stage with backup and dry-run-on-copy.

## Script Safety Review

- mutation source DB possible: no for intended script paths. `migration_status.sh` uses SQLite read-only URI; `migration_check_on_copy.sh` runs `init_db()` against target copy and verifies source SHA.
- source=target refused: yes. `migration_check_on_copy.sh` refuses identical resolved paths with `MIGRATION_COPY_CHECK_ERROR=target_must_not_equal_source`.
- production apply guarded: yes by absence. There is no production apply command in Stage 3 scripts. Policy requires explicit approval before any production DB mutation.
- temp copy behavior verified: yes. Review command copied `data/cs2_coach.db` to `/tmp/jc-coach-stage3-review-migration-check.db`, ran compatibility check on the copy and left source SHA unchanged.

## Changed Files Reviewed

Tracked docs reviewed:

- `docs/BACKUP_RESTORE.md`
- `docs/CHANGELOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_CONTROL.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`

Untracked Stage 3 files reviewed:

- `docs/MIGRATIONS.md`
- `docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md`
- `docs/audit/STAGE_3_MIGRATION_IMPLEMENTATION_REPORT.md`
- `docs/tasks/STABILIZATION_STAGE_3_MIGRATION_DISCIPLINE_TZ_CS2_AI_COACH.md`
- `scripts/migration_check_on_copy.sh`
- `scripts/migration_status.sh`
- `tests/test_migrations.py`

Other untracked file read for context:

- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`

## Test Results

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
bash -n scripts/migration_status.sh
bash -n scripts/migration_check_on_copy.sh
```

Result: both passed.

```bash
PYTHON=.venv/bin/python scripts/migration_status.sh
```

Result: integrity `ok`, user_version `0`, expected project tables listed.

```bash
PYTHON=.venv/bin/python SOURCE_DB=data/cs2_coach.db TARGET_DB=/tmp/jc-coach-stage3-review-migration-check.db scripts/migration_check_on_copy.sh
```

Result: `MIGRATION_COPY_CHECK_RESULT=ok`.

## Production DB Check

Before copy-check:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

After copy-check:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

Production DB SHA unchanged.

## Import/Steam/Parser Jobs Check

No import, Steam or parser production jobs were run.

The full pytest run used Stage 0 test isolation. Steam-related tests in the suite use mocked/unit paths; no production Steam worker or parser job was started by this review.

## Remaining Risks

- No Alembic baseline or migration revision ledger exists yet.
- `Base.metadata.create_all()` and `_upgrade_sqlite_schema()` still run as legacy startup compatibility behavior.
- `migration_check_on_copy.sh` can inspect production DB by default, but it mutates only a copy and verifies source SHA unchanged.
- Future stages that require schema changes must stop and add explicit migration/baseline work first.

## Must Fix Before Stage 4

No blocker if Stage 4 does not change DB schema.

Must fix before Stage 4 only if Stage 4 plans schema changes:

- Add explicit migration implementation path, preferably Alembic baseline, or split schema work into a separate migration stage.
- Run backup and restore verification before applying any production schema change.

## Can Proceed To Stage 4

yes, with constraint: Stage 4 must not introduce schema changes unless migration baseline/tooling is upgraded first.
