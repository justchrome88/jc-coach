# Current Milestone

> Status: Historical / superseded milestone evidence; not current product,
> roadmap, workflow or source-of-truth.
> Use as supporting history only. This file must not override `AGENTS.md`,
> `docs/CURRENT_STATUS.md`, `docs/project_management/WP_REGISTRY.md` or current
> Task Cards.
> Current roadmap/version truth: `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md` and
> `docs/project_management/VERSION_ROADMAP.md`.
> Current workflow truth: `docs/project_management/AGENT_WORKFLOW.md`.
> Navigation/classification: `docs/project_management/DOCS_INDEX.md` and
> `docs/project_management/DOCS_MAP.md`.

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
6. Сделать Steam cursor truth видимой: freshness, stale cursor warnings, retry/backoff status. Stage 7: cursor source/advance/outcome semantics completed / `PASS_WITH_WARNINGS`.
7. Создать metric truth layer: formula, source, confidence и suppression rule по каждой метрике.
8. Усилить parser confidence для early deaths, KAST/trade, side switching и utility attribution.
9. Описать diagnosis registry из verified problems.
10. Собрать recommendation planner из top verified problem snapshots.
11. Добавить structured AI output schema, validator и prompt/version tracking. Stage 8: schema/validator completed / `PASS_WITH_WARNINGS`; prompt/version tracking remains.
12. Сделать dashboard/coach UI с приоритетом next action и primary recommendation. Stage 9: `/coach` coach-first presentation completed / `PASS_WITH_WARNINGS`.

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

## Stage 4 Recommendation Read/Write Split

Status: completed / `PASS_WITH_WARNINGS`.

Goal: GET/read/query recommendation paths do not mutate DB; POST/command paths mutate explicitly.

DoD:

- Recommendation side-effect inventory exists.
- Read/query helpers no longer call `ensure_default_*` or `evaluate_new_matches()`.
- `GET /api/recommendations*` does not create recommendations/evaluations.
- Dashboard/coach read rendering does not create recommendations/evaluations.
- POST status/extend/restart remain explicit mutation paths.
- No schema changes or migrations.
- Safe tests pass.

Warnings:

- This is not recommendation planner.
- Existing multi-category defaults remain until planner work.
- Import/parser ingestion still explicitly initializes/evaluates recommendations after writing matches.

## Stage 5 Metric Truth Layer

Status: completed / `PASS_WITH_WARNINGS`.

Goal: classify runtime metrics by source/formula/reliability/limitations and prevent weak metrics from being treated as fully trusted.

DoD:

- Metric truth inventory exists.
- Runtime metric registry exists in `app/services/metric_truth.py`.
- Core metrics define source, formula, reliability, limitations and usage policy.
- Unknown metrics return safe `unavailable` behavior.
- Low/unavailable metrics are suppressed from hard diagnosis/recommendation.
- `early_deaths` is warning-only for hard recommendation scoring and no longer falls back to `entry_deaths` there.
- AI payload includes metric truth metadata.
- No schema changes or migrations.
- Safe tests pass.

Warnings:

- This is not parser hardening.
- This is not diagnosis registry or recommendation planner.
- Existing rule-based diagnosis still has hardcoded thresholds and needs later registry/planner work.

## Stage 6 Parser Facts & Confidence Hardening

Status: completed / `PASS_WITH_WARNINGS`.

Goal: improve honesty of parser-derived facts and confidence propagation without schema changes or production parser jobs.

DoD:

- Parser facts inventory exists.
- `early_deaths` no longer silently falls back to `entry_deaths`.
- `early_deaths` is filled only from existing timing anchors and remains approximate/warning-only.
- Trade/KAST component, traded deaths, side split and utility/flash limitations are explicit in parser confidence metadata and docs.
- Metric Truth Layer remains conservative; no weak metric was falsely upgraded.
- No schema changes or migrations.
- No production parser/Steam/import jobs.
- Safe tests pass.

Warnings:

- This is not full trade graph implementation.
- Side split/team inference remains low confidence.
- `traded_deaths` / `untraded_deaths` remain unavailable.
- Recommendation planner and AI validator remain future work.

## Stage 7 Steam Cursor Truth

Status: completed / `PASS_WITH_WARNINGS`.

Goal: make Steam match-history cursor behavior deterministic and honest without live Steam calls, production jobs, production DB mutation or schema changes.

DoD:

- Steam cursor inventory exists.
- `steam_accounts.last_share_code` is documented as the saved cursor source of truth.
- Job payload `known_share_code` is a one-job override.
- `knowncode=0` is explicit initial sentinel only when no saved cursor exists.
- Cursor advances only after successful Steam collection and local share-code persistence.
- Failed Steam/API/local persistence paths do not advance cursor.
- No-new, duplicate and error outcomes are documented and tested with mocked paths.
- No schema changes or migrations.
- No live Steam calls or production Steam/import/parser jobs.
- Safe tests pass.

Warnings:

- This is not a durable scheduler, retry ledger or production worker hardening.
- Outcome names describe share-code collection, not guaranteed demo parser completion.
- Service bot demo download and parser import remain separate explicit steps.

## Stage 8 AI Output Validator

Status: completed / `PASS_WITH_WARNINGS`.

Goal: prevent AI coach output from accepting/displaying confident unsupported claims without schema changes or live AI calls.

DoD:

- AI output validation inventory exists.
- Structured output schema/policy exists for `summary`, `diagnoses[]`, `recommendations[]`, `warnings[]`, `evidence[]`, `confidence`.
- Validator checks required structure and Metric Truth Layer usage policy.
- Unknown metric ids are rejected.
- Suppressed/unavailable metrics cannot support hard diagnosis/recommendation claims.
- Approximate/warn metrics require caveats.
- Invalid or free-form AI output gets safe fallback Markdown before persistence/display.
- Tests use mocked outputs only.
- No schema changes, migrations or production DB mutation.
- No live AI calls or production Steam/import/parser jobs.
- Safe tests pass.

Warnings:

- Provider-specific structured response mode is not implemented.
- Prompt/version tracking remains future work.
- This is not recommendation planner, ProblemSnapshot or UI redesign.

## Stage 9 Coach-first UI

Status: completed / `PASS_WITH_WARNINGS`.

Goal: make `/coach` action-first over existing persisted state/services.

DoD:

- `/coach` shows current tracked recommendation first.
- UI labels it honestly as current tracked recommendation, not verified top problem.
- Next-match action, progress, last evaluation and latest match summary are visible when available.
- Metric Truth reliability/warnings are surfaced for weak/approximate/unavailable facts.
- AI validation/fallback status is visible when an AI report exists.
- Safe empty states exist.
- GET `/coach` does not create recommendations/evaluations or run hidden jobs.
- No schema changes, migrations, planner, ProblemSnapshot, parser/Steam/AI engine work or live external jobs.
- Safe tests pass.

Warnings:

- This is not recommendation planner.
- Current recommendation still comes from existing active recommendation ordering/defaults.
- Coach-first UI does not make friends/public readiness claims.
