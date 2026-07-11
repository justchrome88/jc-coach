# WP-012 DB Contamination Guardrails Repair Report

Date: 2026-07-04

RESULT: REPAIRED

## Scope

Minimal repair for findings in `docs/audit/WP_012_DB_CONTAMINATION_GUARDRAILS_DIAGNOSIS.md`.

No production DB cleanup, schema changes, migrations, live AI, Steam, import or parser jobs were performed.

## Baseline Evidence

- Initial `git status --short`: existing untracked `docs/audit/WP_012_DB_CONTAMINATION_GUARDRAILS_DIAGNOSIS.md`.
- Initial DB SHA: `50af6167e0c7b1db05088bef9649db8cf29a20442d6f382af2541271bd733030  data/cs2_coach.db`.
- Service status was inspected by `python3 scripts/project_gate.py preflight`; service was already running and was not restarted.

## Guardrails Added

- Added centralized DB URL safety helpers in `app/config.py`:
  - `is_test_environment()`
  - `database_url_points_to_production()`
  - `assert_test_database_not_production()`
- Reused the new DB helper from `_assert_safe_test_settings()` so APP_ENV=test still fails fast on `data/cs2_coach.db`.
- Added pytest startup protection in `tests/conftest.py` to assert the configured pytest DB is not the production DB before app DB/session imports.
- Added centralized auth email policy in `app/services/auth.py`:
  - `forbidden_test_smoke_email_kind()`
  - `is_forbidden_test_smoke_email()`
  - `assert_registration_email_allowed()`
- `register_user()` now rejects `test-*@example.test` and `smoke-*@example.test` outside `APP_ENV=test`.
- Added `active_credentialed_test_smoke_users()` audit helper to detect unsafe active credentialed test/smoke users.

## Tests Added Or Changed

- `tests/test_auth.py`
  - rejects `test-*@example.test` outside `APP_ENV=test`;
  - rejects `smoke-*@example.test` outside `APP_ENV=test`;
  - allows a normal owner email outside `APP_ENV=test`;
  - allows test/smoke emails in `APP_ENV=test` with test DB settings.
- `tests/test_web_smoke.py`
  - verifies `/register` rejects a smoke email under non-test app settings and creates no user.
- `tests/test_ownership.py`
  - verifies historical inactive/non-credentialed test/smoke users do not affect owner resolution;
  - verifies the new audit helper detects an active credentialed lower-id test/smoke user.
- `tests/test_config.py`
  - verifies production DB URL detection;
  - verifies conftest keeps pytest on `APP_ENV=test` and a non-production DB.

## Docs Updated

- `docs/TESTING.md`: safe pytest command, standalone `TestClient` warning and test/smoke email policy.
- `docs/DEPLOYMENT.md`: read-only smoke separated from mutating/authenticated smoke.
- `docs/PROJECT_GOVERNANCE.md`: production test/smoke registrations are an incident.
- `docs/HANDOFF.md`: owner recovery state and WP-012 DB SHA recorded.
- `docs/BACKUP_RESTORE.md`: backup requirements before users-table cleanup or owner repair.
- `docs/SECURITY.md`: owner policy fragility and test/smoke registration block documented.

## Verification

- `APP_ENV=test .venv/bin/pytest tests/test_auth.py tests/test_ownership.py tests/test_web_smoke.py -q`: `35 passed, 1 warning`.
- `APP_ENV=test .venv/bin/pytest tests -q`: `156 passed, 1 warning`.
- `.venv/bin/ruff check .`: passed.

The warning is the existing Starlette/httpx TestClient deprecation warning.

## DB And Runtime Impact

- Production DB touched: no.
- Production DB mutated: no.
- Schema changed: no.
- Migrations added or run: no.
- Live AI/Steam/import/parser jobs run: no.
- Production service restarted: no.

## Remaining Risks

- Owner policy still depends on first active credentialed user by ascending id. This is guarded better but remains fragile until explicit owner state exists in a future WP.
- Existing historical inactive/non-credentialed test/smoke rows remain in production DB by design; this WP did not authorize cleanup.
- Authenticated production smoke can still mutate `last_login_at`; runbooks now require DB SHA evidence and explicit authorization.

## Can Proceed To Runtime Smoke

yes, for read-only runtime smoke first.

Authenticated or mutating runtime smoke should proceed only with explicit authorization and DB SHA before/after evidence.
