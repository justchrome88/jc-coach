# Stage 2 Ownership Implementation Report

Дата: 2026-07-03.

## STAGE_RESULT

PASS_WITH_WARNINGS

## Owner Policy Chosen

Выбрана политика `first_active_credentialed_user_is_owner`.

Первый активный пользователь с `email` и `password_hash`, созданный через register flow, считается owner single-user инстанса. После появления owner публичная self-registration закрыта и не создаёт второго пользователя. Это не multi-user SaaS и не миграция ownership на все core tables.

## Files Changed

- `app/services/auth.py`
- `app/web/routes.py`
- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_ownership.py`
- `docs/SECURITY.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/STEAM_IMPORT.md`
- `docs/CHANGELOG.md`
- `docs/audit/STAGE_2_OWNERSHIP_IMPLEMENTATION_REPORT.md`

## Tests Added

- Первая регистрация создаёт owner.
- Legacy Steam-only user без credentials не становится owner.
- Вторая регистрация заблокирована по умолчанию.
- Заблокированная вторая регистрация не создаёт запись в БД.
- Web first registration работает, second registration получает ошибку.
- Legacy/non-owner session guard не проходит через `current_user_from_session`.
- Steam OpenID callback без owner session не создаёт uncontrolled user, Steam account или import job.
- Owner session линкует Steam account к owner.
- Bearer `API_TOKEN` остаётся owner/operator path и не создаёт пользователей.

## Safe Checks Results

Выполненные Stage 2 проверки:

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

```bash
sha256sum data/cs2_coach.db
```

Result: `b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c`.

## Production DB Touched

No. Production DB не изменялась. Проверка SHA выполняется read-only.

## Import/Steam/Parser Jobs Run

No. Production import, Steam и parser jobs не запускались.

## Remaining Risks

- `link_steam_account(..., user_id=None)` всё ещё поддерживает legacy service-путь создания Steam-only user. Public OpenID callback больше не использует этот путь без owner session, но helper стоит пересмотреть на отдельном этапе Steam hardening.
- Owner boundary реализован как enforced single-user policy, а не полноценная multi-user ownership модель по всем core tables.
- Rate limiter остаётся in-memory/single-process из Stage 1.
- Friends/public exposure всё ещё запрещён до следующих hardening этапов.

## Can Proceed To Stage 2 Review-Only

yes, если все safe checks проходят и SHA production DB остаётся неизменным.
