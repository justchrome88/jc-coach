# CS2 AI Coach — Stabilization Stage 1 / Security P0 TZ

Дата: 2026-07-03  
Назначение: следующий controlled hardening этап после успешного Stage 0.  
Фокус: закрыть критические security-блокеры без расширения функциональности.

---

# 1. Статус перед Stage 1

Stage 0 считается закрытым, если подтверждено:

- Production DB не изменилась.
- SHA-256 production DB до/после совпал.
- Backup создан.
- Restore проверен на копии.
- Test isolation подтверждён.
- Общий pytest прошёл на temp DB.
- Ruff прошёл.
- `git diff --check` прошёл.
- Импорт, Steam jobs и parser jobs не запускались.

Если любой из этих пунктов не подтверждён — Stage 1 не начинать.

---

# 2. Цель Stage 1

Закрыть P0 security-блокеры:

1. Убрать публичность non-health `/api/*`.
2. Защитить state-changing web/API routes.
3. Ввести CSRF для web POST.
4. Ввести rate limits для login/upload/AI/Steam/import.
5. Ввести strong session secret fail-fast.
6. Верифицировать Steam OpenID callback через `check_authentication`.
7. Закрыть dangerous jobs за auth и логированием.
8. Обновить security docs и release checklist.
9. Подтвердить всё safe tests.

---

# 3. Жёсткие ограничения

В Stage 1 запрещено:

- добавлять новые продуктовые фичи;
- делать viewer, heatmaps, clips, FACEIT, friends/social, public profiles, payments;
- делать Metric Truth Layer;
- делать parser hardening;
- делать recommendation planner;
- делать AI validator;
- делать coach-first UI redesign;
- делать крупные миграции ownership, если они не нужны для security P0;
- менять production DB без отдельного backup;
- запускать import/Steam/parser jobs;
- менять raw demo storage policy.

Stage 1 — это только security P0.

---

# 4. Preflight

Перед изменениями выполнить:

```bash
git status --short
git diff --stat
scripts/backup_runtime.sh
```

Если рабочее дерево грязное не только из-за ожидаемых Stage 0 файлов — остановиться и доложить.

---

# 5. Scope Stage 1

## 5.1. API Auth

Проблема из аудита:

```text
app/main.py:_is_public_path() включает path.startswith("/api/")
```

Это значит, что API фактически public.

Нужно:

1. Найти `_is_public_path()`.
2. Разделить public и protected paths.
3. Public оставить только:
   - `/health`;
   - login/register routes, если нужны;
   - static assets;
   - favicon;
   - возможно OpenID callback, но с отдельной validation logic.
4. Все остальные `/api/*` должны требовать authenticated session или API token.
5. Dangerous API endpoints должны быть protected:
   - import;
   - upload;
   - reports;
   - AI;
   - Steam;
   - storage;
   - recommendation actions;
   - settings.

Acceptance criteria:

- Anonymous request to non-health `/api/*` returns 401/403/redirect-to-login.
- `/health` remains public.
- Static assets remain public.
- Tests cover public/protected behavior.

---

## 5.2. State-changing routes inventory

Создать/обновить security inventory:

```text
docs/audit/API_SECURITY_INVENTORY.md
```

Таблица:

```markdown
| Method | Path | Changes state? | Auth required? | CSRF/API token? | Rate limited? | Notes |
|---|---|---:|---:|---:|---:|---|
```

State-changing includes:

- POST/PUT/PATCH/DELETE;
- import/upload;
- Steam sync/jobs;
- AI generation;
- recommendation status changes;
- settings changes;
- report generation if writes DB;
- storage deletion/cleanup.

---

## 5.3. CSRF for web POST

Нужно:

1. Найти web POST forms.
2. Добавить session-bound CSRF token.
3. Добавить hidden field в templates.
4. Проверять token в state-changing web routes.
5. API token endpoints не обязаны использовать CSRF, если они не cookie-session based.

Acceptance criteria:

- Web POST without CSRF rejected.
- Web POST with valid CSRF accepted.
- Tests added.
- Docs updated.

---

## 5.4. Rate limits

Минимальный MVP rate limit:

- login attempts;
- upload/import;
- AI generation;
- Steam sync/jobs;
- expensive report generation.

Можно сделать in-memory limiter для single-process personal VPS.

Acceptance criteria:

- Rate limit dependency/middleware exists.
- Tests cover limit exceeded for at least login or representative endpoint.
- Docs clearly say MVP limiter is single-process and not public-scale.

---

## 5.5. Strong session secret fail-fast

Проблема:

```text
SESSION_SECRET_KEY default = change-me-before-public-release
```

Нужно:

1. В non-local/non-test env приложение должно падать, если secret default/weak.
2. В local/test можно разрешить default только явно.
3. Обновить `.env.example`.

Acceptance criteria:

- Production-like env + default secret raises error.
- Test/local env allowed.
- Tests added.
- Docs updated.

---

## 5.6. Steam OpenID callback verification

Проблема:

```text
validate_openid_callback() только извлекает openid.claimed_id
```

Нужно:

1. Реализовать Steam OpenID `check_authentication`.
2. Не принимать callback без проверки Steam assertion.
3. Обработать network failure safely.
4. Добавить tests с mocked Steam response.
5. Не запускать реальные Steam jobs.

Acceptance criteria:

- Positive mocked verification passes.
- Negative mocked verification fails.
- Claimed_id-only path no longer links account.
- Docs updated in `docs/STEAM_IMPORT.md` and `docs/SECURITY.md`.

---

## 5.7. Dangerous jobs behind auth/logging

Проверить endpoints/actions:

- Steam sync;
- import;
- parser;
- AI;
- storage cleanup;
- report generation;
- recommendation evaluation.

Нужно:

1. Все state-changing jobs require auth.
2. Все job starts log user/action/time/status.
3. Anonymous job start impossible.

Acceptance criteria:

- Anonymous job start blocked.
- Authenticated user allowed where intended.
- No import/Steam/parser job executed during tests unless mocked.

---

# 6. Tests

Использовать только safe test command из Stage 0.

Минимум тестов:

1. Public `/health` доступен anonymous.
2. Non-health `/api/*` anonymous blocked.
3. Static public.
4. Login route behavior not broken.
5. CSRF missing rejected.
6. CSRF valid accepted for representative route.
7. Default secret fail-fast.
8. Rate limit representative test.
9. Steam OpenID mocked verification positive/negative.
10. Dangerous job anonymous blocked.

Запуск:

```bash
APP_ENV=test ... pytest tests -q
ruff check .
git diff --check
```

Точную команду взять из `docs/TESTING.md`.

---

# 7. Documentation updates

Обновить:

```text
docs/SECURITY.md
docs/RELEASE_CHECKLIST.md
docs/CURRENT_MILESTONE.md
docs/TESTING.md
docs/STEAM_IMPORT.md
docs/CHANGELOG.md
docs/audit/API_SECURITY_INVENTORY.md
```

---

# 8. Verification before finish

В конце показать:

```bash
git status --short
git diff --stat
```

И отчёт:

```text
Stage 1 Security P0 report

Что сделано:
...

Какие P0 закрыты:
...

Какие P0 остались:
...

Какие команды запускались:
...

Production DB была затронута: yes/no
Import/Steam/parser jobs запускались: yes/no
Safe tests:
...

Можно ли переходить к Stage 2:
yes/no
```

---

# 9. Stage 1 DoD

Stage 1 закрыт только если:

- non-health `/api/*` больше не public;
- state-changing endpoints защищены;
- CSRF есть для web POST;
- rate limits есть для login/upload/AI/Steam/import или documented MVP subset;
- strong session secret fail-fast есть;
- Steam OpenID assertion проверяется;
- dangerous jobs behind auth;
- safe tests pass;
- ruff pass;
- git diff check pass;
- docs updated;
- production DB не менялась;
- imports/Steam/parser jobs не запускались.

---

# 10. Стартовый промпт для Codex

```text
Начни Stabilization Stage 1: Security P0.

Перед работой прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_MILESTONE.md
- docs/SECURITY.md
- docs/TESTING.md
- docs/BACKUP_RESTORE.md
- docs/STEAM_IMPORT.md
- docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
- docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
- STABILIZATION_STAGE_1_SECURITY_P0_TZ_CS2_AI_COACH.md

Stage 0 уже завершён:
- production DB hash unchanged;
- backup/restore verified;
- test isolation confirmed;
- pytest passed on temp DB;
- ruff passed;
- git diff --check passed;
- import/Steam/parser jobs were not run.

Цель Stage 1:
закрыть P0 security blockers:
1. protect non-health /api/*;
2. protect state-changing routes;
3. add CSRF for web POST;
4. add rate limits for login/upload/AI/Steam/import;
5. enforce strong session secret fail-fast;
6. verify Steam OpenID callback via check_authentication;
7. protect dangerous jobs behind auth/logging;
8. update docs and tests.

Жёсткие ограничения:
- не добавляй новые продуктовые фичи;
- не делай viewer/heatmaps/clips/FACEIT/friends/public/social/payments;
- не делай Metric Truth Layer, parser hardening, recommendation planner, AI validator или UI redesign;
- не запускай import/Steam/parser jobs;
- не меняй production DB без отдельного backup;
- используй только safe test command из docs/TESTING.md.

Сначала покажи:
- git status --short
- git diff --stat
- план изменений по файлам

Потом реализуй только Stage 1.

В конце покажи:
- что изменено;
- какие P0 закрыты;
- какие P0 остались;
- какие команды запускались;
- была ли затронута production DB;
- запускались ли import/Steam/parser jobs;
- результаты safe tests, ruff и git diff --check;
- можно ли переходить к Stage 2.
```

