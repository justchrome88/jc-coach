# Current Milestone

Last updated: 2026-07-03.

Фактический уровень продукта: `v0.4-alpha foundation`.

Текущий milestone разработки: `v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop`.

## v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop

Goal: make the personal product honest, secure enough for controlled use, and coach-first before expanding scope.

## Sub-phases

1. Заморозить scope вокруг security, metric truth, parser verification и recommendation planner.
2. Изолировать тесты от production DB/settings. Stage 0: guard and safe pytest command are required before broad test runs.
3. Задокументировать и проверить backup/restore до рискованных проверок. Stage 0: backup script and restore-on-copy verification are required before Security P0 work.
4. Закрыть Security P0: API auth, CSRF/state-change hardening, strong secrets.
5. Добавить user ownership или объявленный/принудительный single-user mode для sensitive resources.
6. Сделать Steam cursor truth видимой: freshness, stale cursor warnings, retry/backoff status.
7. Создать metric truth layer: formula, source, confidence и suppression rule по каждой метрике.
8. Усилить parser confidence для early deaths, KAST/trade, side switching и utility attribution.
9. Описать diagnosis registry из verified problems.
10. Собрать recommendation planner из top verified problem snapshots.
11. Добавить structured AI output schema, validator и prompt/version tracking.
12. Сделать dashboard/coach UI с приоритетом next action и primary recommendation.

## Frozen Scope

Until this milestone closes, do not prioritize:

- FACEIT sync.
- Viewer, heatmaps, clips or practice servers.
- Payments, social features or public share pages.
- Raw `.dem` deletion.
- Broad UI polish that does not support the coach loop.

## Done Criteria

- Non-health API routes закрыты auth-ом или explicit token policy.
- Backup/restore process задокументирован и проверен до рискованных проверок.
- User ownership или single-user mode задокументирован и enforced.
- State-changing browser/API actions have CSRF or equivalent same-site protection.
- Strong session secret is enforced outside local development.
- Metric spec exists and unreliable metrics are suppressed from diagnosis.
- Steam import exposes stale cursor/freshness status and retry outcomes.
- Recommendations are created from verified problem evidence.
- AI output is schema-validated or clearly marked unvalidated.
- Tests run without using production DB/settings.

## Stage 0 Safety Foundation DoD

- `git status --short` baseline is understandable before code hardening.
- Docs baseline is not mixed with Security P0/ownership/metric/parser/AI feature work.
- `data/cs2_coach.db` backup can be created by `scripts/backup_runtime.sh`.
- Restore is verified only on a copy by `scripts/restore_runtime.sh --verify-only`.
- `APP_ENV=test .venv/bin/pytest tests -q` is the safe test command.
- `APP_ENV=test` with production `DATABASE_URL` fails fast.
- Import, Steam and parser jobs are not used for Stage 0 validation.

## Stage 1 Security P0 DoD

- Non-health `/api/*` requires authenticated session or configured Bearer `API_TOKEN`.
- State-changing browser POST routes require CSRF.
- Session-authenticated API state changes require CSRF; Bearer API token calls are exempt from browser CSRF.
- Login/upload/import/AI/Steam/report/recommendation/storage mutation routes have MVP in-memory rate limits.
- Non-local/non-test environment rejects default or weak `SESSION_SECRET_KEY`.
- Steam OpenID callback verifies Steam `check_authentication`.
- Dangerous import/Steam/parser/AI/report job starts are anonymous-blocked and logged.
- Safe tests pass with `APP_ENV=test .venv/bin/pytest tests -q`.

## Stage 2 Ownership DoD

Status: completed / `PASS_WITH_WARNINGS`.

- Owner policy выбран и задокументирован: `first_active_credentialed_user_is_owner`.
- Первая регистрация на пустом credentialed-инстансе работает.
- Вторая self-registration по умолчанию заблокирована и не создаёт запись в БД.
- Session auth принимает только owner user.
- Steam OpenID callback без owner session не создаёт uncontrolled second user, Steam account или import job.
- Owner session линкует Steam account только к owner.
- Bearer `API_TOKEN` остаётся owner/operator path и не создаёт пользователей.
- Safe tests проходят только через `APP_ENV=test` и temp DB.

Warnings:

- Это enforced single-owner mode, не полноценный multi-user ownership refactor.
- Legacy `link_steam_account(..., user_id=None)` остаётся later Steam hardening risk.

## Stage 3 Migration Discipline

Status: completed / `PASS_WITH_WARNINGS`.

Goal: define and enforce migration discipline before broader state/schema hardening.

DoD:

- Current schema evolution inventory exists.
- Migration policy is documented in `docs/MIGRATIONS.md`.
- Safe status/copy-check tooling exists.
- Production DB is not mutated.
- Backup-before-migration procedure is documented.
- Future schema changes have an explicit migration path.
- Startup schema mutations are documented as legacy.
- Safe migration/check tests pass.

Warnings:

- Stage 3 scaffold does not implement full Alembic baseline yet.
- `Base.metadata.create_all()` and `_upgrade_sqlite_schema()` remain legacy compatibility paths.
