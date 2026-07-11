# DB Schema Evolution Inventory

Дата: 2026-07-03.

## Verdict

PASS_WITH_WARNINGS.

Stage 3 не меняет production schema. Текущая эволюция схемы остаётся legacy, но теперь есть documented policy и safe copy tooling для будущих changes.

## Current Schema Creation

| Location | Behavior | Status |
|---|---|---|
| `app/db/session.py::engine` | Создаёт global SQLAlchemy engine из `settings.database_url` при импорте | Legacy architecture |
| `app/db/session.py::init_db()` | Вызывает `Base.metadata.create_all(bind=engine)` | Legacy compatibility path |
| `tests/conftest.py` | Создаёт temp app DB и in-memory fixture DB | Safe test isolation |

## Current Startup Schema Mutation

`app/db/session.py::_upgrade_sqlite_schema()` выполняет manual SQLite `ALTER TABLE`, если видит старую локальную схему.

Manual upgrades:

| Table | Columns added by legacy helper |
|---|---|
| `matches` | `early_deaths`, `swing_score` |
| `coach_reports` | `report_type`, `source_ref` |
| `users` | `email`, `password_hash`, `is_active`, `last_login_at` |
| `coach_recommendations` | `start_after_match_id` |

## SQLAlchemy Model Tables

Current ORM model tables:

- `matches`
- `demo_parse_artifacts`
- `demo_rounds`
- `demo_player_rounds`
- `demo_weapon_stats`
- `demo_damage_events`
- `demo_duels`
- `demo_grenade_events`
- `coach_reports`
- `coach_recommendations`
- `match_recommendation_evaluations`
- `users`
- `steam_accounts`
- `import_jobs`
- `app_settings`

## Risks

- Startup can still mutate SQLite schema through legacy helper.
- There is no migration ledger/version table.
- There is no Alembic baseline yet.
- Existing production schema may differ from current ORM models if historical startup upgrades ran at different times.
- Future Metric Truth Layer, parser hardening, Steam cursor truth and AI validator work will likely need new tables/columns.

## Stage 3 New Migration Path

Chosen approach: **Option B — migration discipline scaffold**.

New path:

1. Document schema policy in `docs/MIGRATIONS.md`.
2. Inspect current DB with `scripts/migration_status.sh`.
3. Verify compatibility on a copy with `scripts/migration_check_on_copy.sh`.
4. Require backup/restore verification before any schema change.
5. Do not add new schema changes to `_upgrade_sqlite_schema()`.
6. Adopt Alembic later as an explicit dependency/revision stage.

## What Remains Legacy

- `Base.metadata.create_all(bind=engine)` on startup.
- `_upgrade_sqlite_schema()` manual `ALTER TABLE` compatibility code.
- No formal migration revision ID in production DB.

## Not Changed In Stage 3

- No production DB mutation.
- No model/schema changes.
- No destructive migration.
- No import, Steam or parser production jobs.
