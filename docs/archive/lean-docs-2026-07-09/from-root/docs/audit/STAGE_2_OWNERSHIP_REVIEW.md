# Stage 2 Ownership Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

Stage 2 реализует заявленный enforced single-owner mode без migrations и без multi-user refactor. Ключевые границы закрыты: первая регистрация работает, вторая self-registration блокируется, session auth принимает только owner, public Steam OpenID callback без owner session не создаёт uncontrolled user/account/job, а owner session линкует Steam только к owner.

Статус не `PASS` из-за сохраняющегося legacy internal helper path `link_steam_account(..., user_id=None)`: он больше не достижим из public OpenID callback без owner session, но всё ещё существует как service-level путь и должен быть пересмотрен в отдельном Steam hardening этапе.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | owner policy clearly documented | PASS | `docs/SECURITY.md`, `docs/CURRENT_MILESTONE.md`, `docs/audit/STAGE_2_OWNERSHIP_IMPLEMENTATION_REPORT.md` фиксируют `first_active_credentialed_user_is_owner`. |
| 2 | first user registration works | PASS | `tests/test_ownership.py::test_first_user_registration_works`; safe run: `10 passed`. |
| 3 | second user registration blocked by default | PASS | `register_user()` проверяет `owner_user(db)` до создания пользователя; `test_second_user_registration_blocked_by_default`. |
| 4 | blocked second user does not create DB user | PASS | `test_blocked_second_user_is_not_created_in_db` проверяет, что после blocked registration в `users` остаётся одна запись. |
| 5 | legacy Steam-only user не становится owner | PASS | `owner_user()` требует active user с `email` и `password_hash`; `test_legacy_steam_only_user_does_not_become_owner`. |
| 6 | non-owner/legacy session rejected from owner-only app state | PASS | `current_user_from_session()` вызывает `is_owner_user()`; `test_current_user_from_session_rejects_legacy_non_owner`. |
| 7 | public Steam OpenID callback без owner session не создаёт uncontrolled user/account/job | PASS | `steam_auth_callback()` сначала требует `current_user_from_session`; `test_steam_openid_callback_without_owner_session_does_not_create_uncontrolled_user`. |
| 8 | callback with owner session links Steam only to owner | PASS | callback вызывает `link_steam_account(db, steam_id, user_id=owner.id)`; `test_owner_session_can_link_steam_to_owner`. |
| 9 | API token is documented and behaves as owner/operator token | PASS | `docs/SECURITY.md` документирует `API_TOKEN` как owner/operator token; Stage 1/2 API tests pass. |
| 10 | API token does not create users | PASS | `test_api_token_represents_owner_operator_without_creating_users` проверяет protected `/api/matches` с Bearer token и `users == 0`. |
| 11 | dangerous jobs remain auth/owner protected | PASS | `/api/*` защищены middleware session-or-token policy; web job routes не public и используют owner-only `current_user_from_session`. Stage 1 dangerous-job tests still pass. |
| 12 | Stage 1 API/CSRF/rate-limit behavior still passes | PASS | `APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_steam_integration.py tests/test_web_smoke.py tests/test_ownership.py -q`: `55 passed, 1 warning`. |
| 13 | remaining legacy path `link_steam_account(..., user_id=None)` is not reachable from unsafe public route | PASS_WITH_WARNING | Public OpenID callback now passes `user_id=owner.id` after owner session check. Helper still exists for internal/service/tests. |
| 14 | production DB SHA unchanged | PASS | SHA: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`. |
| 15 | import/Steam/parser production jobs not run | PASS | Review ran only requested pytest/ruff/diff/SHA commands. Steam tests use mocked/unit paths. |
| 16 | safe pytest passed | PASS | `tests/test_ownership.py`: `10 passed`; full `tests`: `100 passed`. |
| 17 | ruff passed | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 18 | git diff --check passed | PASS | `git diff --check`: passed, no output. |

## Legacy Steam Path Risk

- `link_steam_account(..., user_id=None)` всё ещё существует?  
  Yes. В `app/services/steam_integration.py` helper всё ещё создаёт legacy Steam-only `User`, если `user_id` не передан.

- Reachable ли он из public OpenID callback без owner session?  
  No. `app/web/routes.py::steam_auth_callback` сначала требует owner session через `current_user_from_session()`. Без owner session callback возвращает redirect-message и не вызывает `validate_openid_callback()`, `link_steam_account()` или `create_steam_import_job()`.

- Reachable ли он из API/web unsafe path?  
  No для unsafe public path, обнаруженного в Stage 1 review: `/auth/steam/callback` больше не вызывает helper без owner. Web/API job routes защищены Stage 1 middleware и owner/session boundary; Bearer `API_TOKEN` трактуется как owner/operator. Прямые service-level вызовы без `user_id` остаются в unit tests и internal helper usage.

- Это acceptable legacy internal risk или blocker before Stage 3?  
  Acceptable legacy internal risk for Stage 2, not a blocker before Stage 3. Риск должен быть перенесён в Steam hardening: либо запретить default user creation в helper, либо явно разделить legacy test helper и production linking API.

## Changed Files Reviewed

Tracked Stage 2 diff reviewed:

- `app/services/auth.py`
- `app/web/routes.py`
- `docs/CHANGELOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/SECURITY.md`
- `docs/STEAM_IMPORT.md`
- `tests/conftest.py`
- `tests/test_auth.py`

Untracked Stage 2 files reviewed:

- `docs/audit/STAGE_2_OWNERSHIP_IMPLEMENTATION_REPORT.md`
- `docs/tasks/STABILIZATION_STAGE_2_OWNERSHIP_TZ_CS2_AI_COACH.md`
- `tests/test_ownership.py`

Supporting files checked for reachability/security context:

- `app/services/steam_integration.py`
- `app/main.py`
- `docs/audit/STAGE_1_SECURITY_P0_REVIEW.md`
- `docs/audit/API_SECURITY_INVENTORY.md`

## Test Results

```bash
APP_ENV=test .venv/bin/pytest tests/test_ownership.py -q
```

Result: `10 passed, 1 warning`.

```bash
APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_steam_integration.py tests/test_web_smoke.py tests/test_ownership.py -q
```

Result: `55 passed, 1 warning`.

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result: `100 passed, 1 warning`.

```bash
.venv/bin/ruff check .
```

Result: `All checks passed!`.

```bash
git diff --check
```

Result: passed, no output.

## Production DB Check

```bash
sha256sum data/cs2_coach.db
```

Result:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

Production DB SHA unchanged from Stage 2 preflight/report.

## Import/Steam/Parser Jobs Check

No import, Steam or parser production jobs were run.

The Steam-related validation was limited to safe pytest paths. OpenID callback tests monkeypatch `validate_openid_callback`; no live Steam callback verification or production Steam worker was run.

## Remaining Risks

- `link_steam_account(..., user_id=None)` remains as a legacy internal helper path and can still create Steam-only `User` records when called directly from service code/tests.
- Single-owner mode is enforced at auth/session and public callback boundaries, not by adding `user_id` ownership to every core table.
- `PROJECT_CONTROL.md` still describes ownership/single-user enforcement as next in one status sentence; after commit/review, canonical project status should be refreshed to mark Stage 2 complete.
- Rate limiter remains in-memory/single-process from Stage 1.
- Recommendation read endpoints can still have write side effects through existing services; this is outside Stage 2.

## Must Fix Before Stage 3

No blocker found for proceeding to Stage 3 review/next hardening stage.

Recommended non-blocking follow-ups:

- Update canonical status docs after Stage 2 commit/review so `PROJECT_CONTROL.md` no longer says ownership remains next.
- During Steam hardening, remove or restrict production use of `link_steam_account(..., user_id=None)`.
- Keep Stage 3 limited to the next milestone item; do not start Metric Truth Layer/parser/AI/UI work unless Stage 3 explicitly targets it.

## Can Proceed To Stage 3

yes
