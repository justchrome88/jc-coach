# Testing

Last updated: 2026-07-03.

## Current Truth

Test isolation is now a Stage 0 safety requirement. Tests must run with `APP_ENV=test` and a non-production SQLite database.

`tests/conftest.py` forces `APP_ENV=test` and defaults `DATABASE_URL` to a temp DB under `/tmp`. If a caller explicitly sets `DATABASE_URL` to the production path `data/cs2_coach.db`, app settings fail fast.

## Safe Commands

Recommended full safe test command:

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Targeted safe command while working on test isolation:

```bash
APP_ENV=test .venv/bin/pytest tests/test_config.py tests/test_web_smoke.py -q
```

Static check:

```bash
ruff check .
```

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

Do not run tests by invoking the app against the default runtime `.env` or `data/cs2_coach.db`.

## Rules

- Do not run parser jobs, Steam jobs or import jobs during documentation-only tasks.
- Tests must not use production DB/settings.
- `APP_ENV=test` with production `DATABASE_URL` must fail.
- `TestClient(app)` must use the temp test DB created by pytest configuration, not `data/cs2_coach.db`.
- For Python route/template changes, perform live smoke checks only when the task explicitly involves runtime behavior and it is safe to start/restart the app.

## Isolation Guarantees

- Test runtime DB: `/tmp/jc-coach-pytest-<pid>/cs2_coach_test.db` by default.
- Test upload/inbox/reports/AI handoff dirs: `/tmp/jc-coach-pytest-<pid>/...`.
- Production DB path guard: `app.config._assert_safe_test_settings`.
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
- Steam cursor handling and job status without real external jobs.
- Steam OpenID verification with mocked Steam responses only.
- Migration status/copy tooling against temp DB or copied DB only.

## Forbidden During Stage 0

- Import jobs.
- Steam jobs.
- Parser jobs against real demos.
- Tests or smoke checks that touch `data/cs2_coach.db`.
