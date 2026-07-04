# WP-012 DB Contamination Guardrails Diagnosis

Date: 2026-07-04

RESULT: DIAGNOSED

## Current Production DB State

- Production DB SHA before diagnosis: `50af6167e0c7b1db05088bef9649db8cf29a20442d6f382af2541271bd733030  data/cs2_coach.db`.
- Read-only inspection found `254` rows in `users`.
- Current active credentialed owner candidate is `id=17`, `email=justchrome88@yandex.ru`, `display_name=Станислав`.
- `test-%@example.test`: `248` total, `0` active credentialed.
- `smoke-%@example.test`: `4` total, `0` active credentialed.
- There is `1` legacy/null-email user, not credentialed and not an owner candidate.
- Current owner policy therefore resolves to the real owner, but only because test/smoke rows have been deactivated and their password hashes cleared.

## Root Cause

The contamination was possible because production runtime defaults to `data/cs2_coach.db` unless test settings are explicitly active, while test/web smoke helpers create real credentialed users through the normal register path.

Direct tracked creator for `test-*@example.test`:

- `tests/test_web_smoke.py:24` defines `_register_test_user()`.
- `tests/test_web_smoke.py:31` posts `email=f"test-{uuid4().hex}@example.test"`.
- The helper is used by multiple web smoke tests, so one unsafe run can create several rows.

Other tracked test user creators:

- `tests/test_auth.py` creates `user@example.test` through `register_user()`.
- `tests/test_ownership.py` creates `owner@example.test`, `owner-web@example.test`, `second-web@example.test`, `owner-steam@example.test` and direct `legacy@example.test` users.
- `tests/test_coach_first_ui.py` and `tests/test_recommendation_read_write_split.py` register `owner@example.test` through the web flow.

No tracked source currently creates `smoke-*@example.test`. The production rows have `display_name=Smoke`, so the most likely source is an ad hoc live runtime smoke command or untracked script that posted to `/register` with `smoke-$(...)@example.test`.

## Affected Files

- `app/config.py`: default `app_env` is `local` and default `database_url` is `sqlite:///data/cs2_coach.db`; the production DB guard only runs when `APP_ENV=test`.
- `app/db/session.py`: module import builds the global engine from current settings; `init_db()` can create/upgrade schema on whatever DB the engine points at.
- `app/services/auth.py`: `register_user()` creates active credentialed users; `owner_user()` selects the first active credentialed user by ascending id.
- `app/web/routes.py`: `POST /register` calls `register_user()` and logs the new user in.
- `tests/conftest.py`: now forces `APP_ENV=test` and temp DB before app imports, but this is pytest-local protection.
- `tests/test_web_smoke.py`: creates random `test-*@example.test` users via web registration.
- `scripts/*`: no tracked script creates users. `migration_status.sh` is read-only; `migration_check_on_copy.sh` runs `init_db()` only on a copied DB; backup/restore scripts do not create users.

## Current Test Isolation Risk

Current pytest isolation is mostly safe when tests are run normally through pytest:

- `tests/conftest.py:18` sets `APP_ENV=test`.
- `tests/conftest.py:19` defaults `DATABASE_URL` to `/tmp/jc-coach-pytest-<pid>/cs2_coach_test.db`.
- `app/config.py:68` rejects `APP_ENV=test` when `DATABASE_URL` resolves to `data/cs2_coach.db`.

Residual risk remains:

- Running the app or test helpers outside pytest uses `app/config.py` defaults and can hit production DB.
- Running live runtime smoke against the real service and posting `/register` mutates production users.
- The safety guard is test-mode-only; production/local mode has no deny-list for `example.test` users and no explicit "test code cannot register users" guard.
- `TestClient(app)` is safe inside pytest only because conftest runs before app imports. It is not intrinsically safe as a standalone Python snippet.

Conclusion: current `pytest tests` without externally setting `APP_ENV=test` should use temp DB because `conftest.py` forces it. The higher risk is non-pytest smoke/test code, historical runs before this isolation existed, or live service registration smoke.

## Owner Policy Risk

Current policy:

- `OWNER_POLICY = "first_active_credentialed_user_is_owner"` in `app/services/auth.py`.
- `owner_user()` filters `is_active == 1`, `email IS NOT NULL`, `password_hash IS NOT NULL`, then orders by `id ASC`.

Risk:

- Any active credentialed test/smoke user with an id lower than the real owner becomes owner.
- A polluted owner candidate blocks the real owner from login because `authenticate_user()` rejects non-owner credentialed users.
- Deactivating users and clearing password hashes restores owner resolution, but this is a manual data repair, not a guardrail.
- The policy is brittle because ownership is inferred from mutable user data and insertion order rather than an explicit owner marker/configuration.

## Minimal Repair Plan

1. Add a production/runtime registration guard that rejects `test-*@example.test` and `smoke-*@example.test` users outside `APP_ENV=test`.
2. Add an explicit DB safety helper that refuses test/smoke execution when settings resolve to `data/cs2_coach.db`, not only when `APP_ENV=test`.
3. Make runtime smoke guidance read-only by default: unauthenticated GET `/health`, `/`, redirect checks only; no `/register`, `/login`, import, parser, Steam or AI jobs unless explicitly authorized.
4. Add a safe authenticated smoke mechanism for production that does not create users and does not POST login, or require manual owner browser verification with DB SHA before/after.
5. Replace owner inference in a later controlled pass with an explicit owner setting/flag, or at minimum add a startup/audit check that fails loudly when more than one active credentialed user exists.
6. Keep any production data cleanup as a separately approved DB repair with backup, DB SHA before/after and rollback instructions.

## Required Regression Tests

- Config/settings test: production DB URL is rejected for any pytest/test runner context even if `APP_ENV` is missing or mis-set.
- Auth test: `register_user()` rejects `test-*@example.test` and `smoke-*@example.test` outside `APP_ENV=test`.
- Web route test: `POST /register` cannot create test/smoke users in non-test app settings.
- Test isolation test: `TestClient(app)` startup points to temp DB and never to `data/cs2_coach.db`.
- Owner policy test: a lower-id active credentialed non-owner/test user is detected as unsafe, not silently accepted.
- Runtime smoke script/test: read-only smoke commands do not change DB SHA and do not create users.
- Script scan/static test: tracked smoke/runtime scripts must not contain live `/register` user creation against production URLs.

## Required Docs/Runbook Updates

- `docs/TESTING.md`: state that safe pytest must be `APP_ENV=test .venv/bin/pytest tests -q`; forbid standalone `TestClient` snippets unless they set temp DB before app import.
- `docs/DEPLOYMENT.md`: split smoke checks into read-only smoke and mutating/authenticated smoke; require DB SHA before/after any authenticated runtime check.
- `docs/PROJECT_GOVERNANCE.md`: add explicit prohibition on test/smoke registrations in production DB.
- `docs/HANDOFF.md`: record current owner recovery state and the exact current production DB SHA.
- `docs/BACKUP_RESTORE.md`: require backup before any users-table cleanup or owner repair.
- `docs/SECURITY.md`: document that current owner policy is insertion-order based and fragile until explicit owner state is implemented.

## Can Proceed To Repair

yes

Proceed only with an explicit repair-mode WP. Do not mutate production DB during repair unless the prompt authorizes it and backup/rollback evidence is recorded.
