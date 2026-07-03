# Stage 1 Security P0 Review

Дата проверки: 2026-07-03.

## STAGE_RESULT

**PASS_WITH_WARNINGS**

Stage 1 в целом закрывает заявленные Security P0 пункты: non-health `/api/*` больше не public, web/API state changes защищены CSRF/auth правилами, добавлены MVP rate limits, strong session secret fail-fast и Steam OpenID `check_authentication`.

Предупреждения:

- Bearer `API_TOKEN` path реализован по коду, но отдельного automated test на Bearer token без CSRF в Stage 1 diff нет.
- `/auth/steam/callback` остаётся public и state-changing по природе OpenID callback: он может линковать Steam account и создавать `steam_openid_linked` job record после успешной Steam assertion verification. Это допустимое Stage 1 исключение, но ownership/single-user mode должен закрыть его последствия на Stage 2.
- MVP rate limiter process-local; это честно задокументировано и не является public-scale защитой.
- Recommendation read endpoints всё ещё могут иметь write side effects через старые service helpers; это не Stage 1 fix, но важно перед Stage 2/Planner.

## Evidence by DoD Item

| # | DoD item | Result | Evidence |
|---:|---|---|---|
| 1 | non-health `/api/*` больше не public | PASS | `app/main.py` больше не включает `path.startswith("/api/")` в `_is_public_path`; middleware `enforce_security` обрабатывает `/api/*` до public-path логики. |
| 2 | `/health` остаётся public | PASS | `_is_public_path` содержит `/health`; `tests/test_web_smoke.py::test_health_endpoint` проходит. |
| 3 | static assets/login/register/openid callback не сломаны | PASS_WITH_WARNING | `_is_public_path` оставляет `/`, `/login`, `/register`, `/static/*`, `/language/*`, `/auth/steam/callback`; login/register smoke tests проходят. OpenID callback теперь fail-closed при недоступности Steam. |
| 4 | anonymous non-health `/api/*` получает 401/403/redirect | PASS | `tests/test_web_smoke.py::test_api_requires_authentication_for_anonymous_user` ожидает `401`; `test_dangerous_api_job_anonymous_blocked` ожидает `401`. |
| 5 | state-changing routes требуют auth | PASS_WITH_WARNING | Non-public web routes проходят auth middleware после CSRF; `/api/*` требует session/API token. Public state-changing exceptions: `/login`, `/register`, `/auth/steam/callback`; callback защищён Steam assertion, но не session auth. |
| 6 | CSRF есть для browser POST | PASS | `csrf_token` добавлен в template context и hidden fields во все найденные POST forms; `test_csrf_missing_rejected_for_web_post` ожидает `403`. |
| 7 | session-authenticated API state changes требуют `X-CSRF-Token` | PASS | `app/main.py` проверяет `has_valid_csrf` для API POST при session user без API token; `test_session_api_post_requires_csrf` ожидает `403`. |
| 8 | Bearer API token path работает без CSRF | PASS_WITH_WARNING | `app/main.py` пропускает CSRF, если `has_valid_api_token(..., settings.api_token)` true. Автотеста на этот path нет. |
| 9 | rate limits есть для login/upload/import/AI/Steam/report/recommendation/storage mutation routes или documented MVP subset | PASS | `app/services/security.py::rate_limit_bucket` покрывает эти bucket-и; `docs/SECURITY.md` и `docs/audit/API_SECURITY_INVENTORY.md` документируют MVP single-process limiter. Тест покрывает login representative case. |
| 10 | strong session secret fail-fast есть для non-local/non-test env | PASS | `app/config.py::_assert_strong_session_secret`; `tests/test_security.py` покрывает production-like reject и local allow. |
| 11 | Steam OpenID callback проверяет `check_authentication`, а не только `claimed_id` | PASS | `app/services/steam_integration.py::_verify_openid_assertion`; tests cover positive/negative mocked Steam response. |
| 12 | dangerous jobs behind auth/logging | PASS_WITH_WARNING | API job routes anonymous-blocked before route execution; `log_security_event` logs API/web state changes. Web Steam job routes require session auth. OpenID callback creates a non-running `steam_openid_linked` job record as public callback exception. |
| 13 | safe pytest passed | PASS | `APP_ENV=test .venv/bin/pytest tests -q`: `88 passed, 1 warning`. |
| 14 | ruff passed | PASS | `.venv/bin/ruff check .`: `All checks passed!`. |
| 15 | git diff --check passed | PASS | `git diff --check`: no output, exit 0. |
| 16 | production DB SHA unchanged | PASS | `sha256sum data/cs2_coach.db`: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`. |
| 17 | import/Steam/parser production jobs не запускались | PASS | Review ran only requested safe pytest/ruff/diff/SHA commands. No import/Steam/parser job command was run. |

## Changed Files Reviewed

Reviewed tracked Stage 1 diff:

- `.env.example`
- `app/config.py`
- `app/main.py`
- `app/services/steam_integration.py`
- `app/templates/base.html`
- `app/templates/coach.html`
- `app/templates/import_settings.html`
- `app/templates/login.html`
- `app/templates/register.html`
- `app/templates/report.html`
- `app/templates/storage_settings.html`
- `app/templates/upload.html`
- `docs/CHANGELOG.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/PROJECT_CONTROL.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/SECURITY.md`
- `docs/STEAM_IMPORT.md`
- `docs/TESTING.md`
- `tests/conftest.py`
- `tests/test_steam_integration.py`
- `tests/test_web_smoke.py`

Reviewed untracked Stage 1 files:

- `app/services/security.py`
- `tests/test_security.py`
- `docs/audit/API_SECURITY_INVENTORY.md`

Untracked task file observed but not treated as implementation:

- `STABILIZATION_STAGE_1_SECURITY_P0_TZ_CS2_AI_COACH.md`

## Test Results

Commands run exactly from the review request:

```bash
APP_ENV=test .venv/bin/pytest tests/test_security.py -q
```

Result:

```text
3 passed, 1 warning
```

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_web_smoke.py tests/test_security.py -q
```

Result:

```text
43 passed, 1 warning
```

```bash
APP_ENV=test .venv/bin/pytest tests -q
```

Result:

```text
88 passed, 1 warning
```

```bash
.venv/bin/ruff check .
```

Result:

```text
All checks passed!
```

```bash
git diff --check
```

Result: passed, no output.

## Production DB Check

Command:

```bash
sha256sum data/cs2_coach.db
```

Result:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c  data/cs2_coach.db
```

This matches the Stage 0/Stage 1 reported production DB SHA. No DB-changing command was run during review.

## Import/Steam/Parser Jobs Check

No import, Steam or parser production jobs were run during this review.

The only Steam-related checks were unit tests with mocked Steam OpenID responses in `tests/test_steam_integration.py`. The full safe pytest suite uses Stage 0 test isolation and temp DB paths.

## Remaining Risks

- User ownership or enforced single-user mode is still not implemented. This remains the main blocker before broader controlled use.
- OpenID callback remains a public state-changing callback by design; it now verifies Steam assertion but still needs ownership/single-user boundaries.
- Bearer API token path lacks direct automated test coverage.
- Rate limiter is in-memory and single-process.
- CSRF extraction for multipart forms is a minimal parser over request body. Tests pass, but this should be watched when upload handling changes.
- API recommendation reads can still mutate DB via existing recommendation helpers.
- Security event logging uses standard app logging, not a durable audit table.

## Must Fix Before Stage 2

Required before or at start of Stage 2:

1. Add direct test coverage for Bearer `API_TOKEN` access without CSRF.
2. Decide and implement enforced single-user mode or ownership boundaries for matches, reports, recommendations, Steam accounts and jobs.
3. Include `/auth/steam/callback` behavior in Stage 2 ownership/single-user review because it creates records from a public callback.

## Can Proceed To Stage 2

**yes**

Proceed only to Stage 2 ownership/enforced single-user boundaries. Do not start Metric Truth Layer, parser hardening, recommendation planner, AI validator or UI redesign from this review.

## Addendum: Bearer API_TOKEN Coverage Repair

Дата: 2026-07-03.

Repair scope: закрыт один warning из review — отсутствовал direct automated test для Bearer `API_TOKEN` без CSRF.

Что добавлено:

- `tests/test_security.py::test_bearer_api_token_allows_protected_api_without_csrf`
- `tests/test_security.py::test_invalid_bearer_api_token_is_rejected`

Поведение продукта не менялось. Текущая реализация уже пропускала валидный Bearer token без `X-CSRF-Token` и отклоняла invalid token; добавлены только тесты.

Stage 1 status after repair: **PASS_WITH_WARNINGS**.

Снятый warning:

- Bearer `API_TOKEN` path теперь имеет direct automated test coverage.

Оставшиеся warnings:

- `/auth/steam/callback` остаётся public state-changing callback и должен быть учтён в Stage 2 ownership/single-user review.
- MVP rate limiter process-local.
- Recommendation read endpoints всё ещё могут иметь write side effects через старые service helpers.
