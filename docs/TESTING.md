# Testing

Last updated: 2026-07-04.

## Current Truth

Test isolation is now a Stage 0 safety requirement. Tests must run with `APP_ENV=test` and a non-production SQLite database.

`tests/conftest.py` forces `APP_ENV=test` and defaults `DATABASE_URL` to a temp DB under `/tmp`. If a caller explicitly sets `DATABASE_URL` to the production path `data/cs2_coach.db`, app settings fail fast.

Standalone `TestClient` snippets are forbidden unless `APP_ENV=test`, `DATABASE_URL` and runtime artifact directories are configured to temp paths before importing `app.main` or `app.db.session`. Importing the app first can bind the global SQLAlchemy engine to the default runtime DB.

## Safe Commands

Recommended full safe test command:

```bash
APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
```

Targeted safe command while working on test isolation:

```bash
APP_ENV=test .venv/bin/pytest tests/test_config.py tests/test_web_smoke.py -q
```

Static check:

```bash
.venv/bin/ruff check . --no-cache
```

Mandatory local quality gate command:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

`scripts/local_quality_gate.py` is the standard local command to run before an
Executor claims PASS on code, script or test changes. It runs project gate
preflight, changed and required-checks evidence; the full safe pytest command
with `APP_ENV=test` and `PYTHONDONTWRITEBYTECODE=1`; Ruff; `git diff --check`;
and project gate postflight. The command returns non-zero if any required
subcommand fails.

Project gate preflight/postflight commands:

```bash
.venv/bin/python scripts/project_gate.py preflight
.venv/bin/python scripts/project_gate.py changed
.venv/bin/python scripts/project_gate.py required-checks
.venv/bin/python scripts/project_gate.py postflight
```

`project_gate.py` is a read-only report helper. It records task-start and
task-close evidence such as working directory, branch, recent commits,
`git status --short -uall`, changed/untracked files, inferred guardians,
required/recommended checks, governance file presence, diff stat and the
production DB SHA. It does not run services, imports, parser jobs, evaluator
jobs, package installs or DB mutations.

For code, test or script changes, task reports should include the project gate
commands, the focused relevant tests, the full safe test suite, Ruff and
`git diff --check` unless the task card gives stricter instructions.

Migration discipline checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_migrations.py -q
bash -n scripts/migration_status.sh
bash -n scripts/migration_check_on_copy.sh
```

Metric Truth Layer targeted checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
```

Parser facts confidence checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
```

Steam cursor truth checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_cursor_truth.py -q
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_security.py tests/test_ownership.py tests/test_steam_cursor_truth.py -q
```

AI Output Validator checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q
```

Coach-first UI checks:

```bash
APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
```

Do not run tests by invoking the app against the default runtime `.env` or `data/cs2_coach.db`.

## Rules

- Do not run parser jobs, Steam jobs or import jobs during documentation-only tasks.
- Tests must not use production DB/settings.
- `APP_ENV=test` with production `DATABASE_URL` must fail.
- Test/smoke registration emails (`test-*@example.test`, `smoke-*@example.test`) are allowed only in `APP_ENV=test` with a non-production DB.
- `TestClient(app)` must use the temp test DB created by pytest configuration, not `data/cs2_coach.db`.
- For Python route/template changes, perform live smoke checks only when the task explicitly involves runtime behavior and it is safe to start/restart the app.

## Isolation Guarantees

- Test runtime DB: `/tmp/jc-coach-pytest-<pid>/cs2_coach_test.db` by default.
- Test upload/inbox/reports/AI handoff dirs: `/tmp/jc-coach-pytest-<pid>/...`.
- Production DB path guard: `app.config._assert_safe_test_settings`.
- Pytest DB path guard: `tests/conftest.py` calls `app.config.assert_test_database_not_production()` before importing app DB/session modules.
- Web smoke tests may import `app.main`, but startup `init_db()` must target the temp test DB.

## Coverage Priorities

- API auth, CSRF, rate limits and strong secret fail-fast.
- Import tolerance and dedupe.
- Analytics and metric confidence.
- Metric Truth Layer reliability/suppression policy.
- Parser-derived fact confidence and weak-fact suppression.
- Recommendation lifecycle and evaluation.
- AI payload/result persistence.
- AI output validation with mocked provider/output only.
- Coach-first UI rendering and GET/read no-mutation behavior.
- Steam cursor handling and job status without real external jobs.
- Steam OpenID verification with mocked Steam responses only.
- Migration status/copy tooling against temp DB or copied DB only.

## Forbidden During Stage 0

- Import jobs.
- Steam jobs.
- Parser jobs against real demos.
- Tests or smoke checks that touch `data/cs2_coach.db`.
