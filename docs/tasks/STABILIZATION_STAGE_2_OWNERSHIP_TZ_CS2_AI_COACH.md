# CS2 AI Coach — Stabilization Stage 2 / Ownership & Enforced Single-Owner Boundaries TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 2 после закрытия Stage 1 Security P0.  
Фокус: явно закрепить single-owner модель и не дать register/OpenID/API создать неконтролируемые данные чужого пользователя.

---

# 1. Статус перед Stage 2

Stage 2 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] git status clean or only expected Stage 2 task file is untracked
[✓] safe pytest green
[✓] production DB hash known
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -5
sha256sum data/cs2_coach.db
```

Если есть незакоммиченные изменения после Stage 1 — Stage 2 не начинать.

---

# 2. Главная цель Stage 2

Сейчас проект не готов к настоящему multi-user режиму, потому что core tables ещё не имеют полноценного `user_id` ownership:

```text
Match
CoachReport
CoachRecommendation
MatchRecommendationEvaluation
ImportJob
часть Steam/report/recommendation/runtime сущностей
```

Полноценный multi-user ownership сейчас преждевременен, потому что migration discipline ещё не закрыт.

Поэтому Stage 2 делает не SaaS multi-user, а:

```text
enforced single-owner instance
```

То есть приложение явно работает как один персональный инстанс:

```text
один owner user владеет локальным состоянием приложения;
новые пользователи не могут самовольно создаваться и смешиваться с owner state;
public OpenID callback не может создать/привязать чужое состояние вне owner boundary;
API/web routes не дают second user получить или мутировать owner data.
```

---

# 3. Не цель Stage 2

Запрещено делать:

- полноценный multi-user SaaS;
- массовое добавление `user_id` во все core tables;
- Alembic/migration discipline;
- Metric Truth Layer;
- parser hardening;
- recommendation planner;
- recommendation read/write split;
- AI validator;
- coach-first UI redesign;
- viewer/heatmaps/clips;
- FACEIT;
- friends/social/public profiles;
- payments;
- production import/Steam/parser jobs.

Если Codex считает, что без migration нельзя — он должен остановиться и написать `BLOCKED`, а не импровизировать.

---

# 4. Предпочтительное архитектурное решение

Предпочтительный режим:

```text
single_owner_mode = enforced
```

Минимальная допустимая модель:

1. В приложении есть один owner user.
2. Если owner user уже существует, самостоятельная регистрация новых пользователей запрещена или требует явной политики.
3. Login разрешён существующему owner.
4. Register:
   - либо disabled после создания первого пользователя;
   - либо разрешён только если пользователей нет;
   - либо invite/admin-token based, если уже предусмотрено простым и безопасным способом.
5. Steam OpenID callback:
   - не должен создавать нового arbitrary user, если owner уже существует;
   - должен привязывать Steam account только к owner/current user согласно политике;
   - public callback не должен создавать uncontrolled second user.
6. API/web current_user:
   - second/non-owner user не должен иметь доступ к owner state;
   - если second user невозможен, это должно быть enforced and tested.
7. Документация должна честно говорить:
   - это не multi-user;
   - это personal/single-owner protected instance;
   - friends alpha требует отдельного gate.

---

# 5. Stage 2 scope

## 5.1. Owner policy

Найти текущие auth/user модели и registration flow.

Проверить:

```bash
rg -n "User|register|login|current_user|get_current_user|SteamAccount|link_steam|openid|user_id|owner|single" app tests docs
```

Сформулировать и реализовать owner policy.

Возможные варианты:

```text
Option A: first user is owner; registration disabled after owner exists.
Option B: first user is owner; additional registration requires explicit REGISTRATION_ENABLED=true.
Option C: owner id configured by env/settings.
```

Предпочтительно для текущего проекта:

```text
Option A + explicit config flag if already easy.
```

Не усложнять.

## 5.2. Registration boundary

Нужно:

- запретить самовольное создание второго пользователя после owner;
- вернуть понятную ошибку/страницу;
- не сломать создание первого пользователя на пустом инстансе;
- обновить tests.

Acceptance criteria:

```text
[ ] first user registration works on empty DB
[ ] second user registration blocked by default
[ ] blocked registration does not create DB user
[ ] docs explain registration policy
```

## 5.3. Current user / owner boundary

Нужно:

- определить функцию/guard, которая проверяет, что текущий user является owner;
- применить её там, где state является instance-wide;
- не делать массовый multi-user refactor.

Acceptance criteria:

```text
[ ] owner user can access protected app
[ ] non-owner user cannot access/mutate owner state
[ ] if non-owner users are impossible, tests prove registration block
[ ] API auth from Stage 1 still works
```

## 5.4. Steam OpenID callback boundary

Из Stage 1 review:

```text
/auth/steam/callback остаётся public и state-changing по природе OpenID callback.
Он теперь проверяет Steam assertion, но ownership/single-user consequences должны быть закрыты Stage 2.
```

Нужно:

- проверить `validate_openid_callback`, `link_steam_account`, callback route;
- запретить public callback создавать arbitrary second user, если owner уже существует;
- если callback приходит без текущей session:
  - либо привязывать только к existing owner under explicit pending login flow;
  - либо fail closed;
  - либо показывать безопасную ошибку;
- не запускать реальные Steam jobs.

Acceptance criteria:

```text
[ ] mocked positive OpenID callback cannot create uncontrolled second user
[ ] callback with owner session links to owner only
[ ] callback without valid owner/session behaves according to documented policy
[ ] tests cover this
```

## 5.5. ImportJob / job boundary

Без миграций и массового ownership:

- убедиться, что job-start endpoints требуют owner/current user;
- если job records имеют nullable/no `user_id`, не пытаться мигрировать всё в Stage 2;
- documented limitation acceptable, если dangerous job start is owner-only.

Acceptance criteria:

```text
[ ] dangerous jobs require owner boundary
[ ] no anonymous or non-owner job start
[ ] no production jobs run during tests
```

## 5.6. API token boundary

Если Stage 1 добавил Bearer `API_TOKEN`, Stage 2 должен определить его owner semantics:

```text
Bearer API_TOKEN represents instance owner/operator.
```

Acceptance criteria:

```text
[ ] docs state API_TOKEN is owner/operator token
[ ] API token does not create users
[ ] API token cannot bypass owner policy in unsafe ways
```

---

# 6. Tests to add/update

Добавить или обновить tests, предпочтительно:

```text
tests/test_ownership.py
```

Минимум:

1. First user registration allowed on empty DB.
2. Second user registration blocked by default.
3. Blocked second registration does not create user.
4. Non-owner user cannot access representative protected owner route, if non-owner can be created in tests.
5. Steam OpenID callback mocked:
   - owner session links to owner;
   - no-session callback does not create uncontrolled user if owner exists.
6. API token still works as owner/operator token.
7. Existing Stage 1 tests still pass.

Если test setup не позволяет просто создать non-owner user через public register, можно создать user напрямую через fixture and verify middleware/guard blocks where relevant.

---

# 7. Documentation updates

Обновить:

```text
docs/SECURITY.md
docs/CURRENT_MILESTONE.md
docs/RELEASE_CHECKLIST.md
docs/TESTING.md если меняется test command/setup
docs/STEAM_IMPORT.md если меняется OpenID callback behavior
docs/CHANGELOG.md
```

Создать:

```text
docs/audit/STAGE_2_OWNERSHIP_IMPLEMENTATION_REPORT.md
```

или обновить existing stage report, если Codex создаёт один.

---

# 8. Safe checks

Запускать только safe tests:

```bash
APP_ENV=test .venv/bin/pytest tests/test_ownership.py -q
APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_steam_integration.py tests/test_web_smoke.py tests/test_ownership.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Не запускать:

```text
production import
Steam sync
parser jobs
demo parsing
production server jobs
```

---

# 9. Stage 2 DoD

Stage 2 считается реализованным только если:

```text
[ ] owner policy chosen and documented
[ ] first user registration policy works
[ ] second user registration blocked or explicitly controlled
[ ] public OpenID callback cannot create uncontrolled second user
[ ] owner/current_user boundary exists and is tested
[ ] API token owner/operator semantics documented
[ ] dangerous jobs remain owner/auth protected
[ ] Stage 1 API/CSRF/rate-limit behavior still passes
[ ] safe pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] production DB SHA unchanged unless explicitly allowed
[ ] import/Steam/parser production jobs not run
[ ] docs updated
[ ] implementation report created
```

---

# 10. Start prompt for Codex

```text
Начни Stage 2: Ownership / enforced single-user boundaries.

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
- docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
- docs/audit/API_SECURITY_INVENTORY.md
- docs/tasks/STABILIZATION_STAGE_2_OWNERSHIP_TZ_CS2_AI_COACH.md

Stage 0 завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.

Цель Stage 2:
реализовать enforced single-user / single-owner boundaries, не полноценный multi-user SaaS.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -5
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Реализуй только Stage 2:
1. определить owner user policy;
2. запретить/ограничить регистрацию новых пользователей согласно owner policy;
3. закрыть риск, что /auth/steam/callback создаёт/линкует чужие данные вне owner boundary;
4. добавить owner/current_user boundary checks;
5. добавить tests на first user, blocked second user, Steam callback owner boundary, API token owner semantics;
6. обновить docs/SECURITY.md, docs/CURRENT_MILESTONE.md, docs/RELEASE_CHECKLIST.md, docs/STEAM_IMPORT.md при необходимости, docs/CHANGELOG.md;
7. создать docs/audit/STAGE_2_OWNERSHIP_IMPLEMENTATION_REPORT.md.

Жёсткие ограничения:
- не делать полноценный multi-user ownership через массовое добавление user_id во все core tables;
- не делать migrations без отдельного explicit migration stage;
- не делать Metric Truth Layer;
- не делать parser hardening;
- не делать recommendation planner;
- не делать AI validator;
- не делать UI redesign;
- не запускать import/Steam/parser production jobs;
- не менять production DB без отдельного backup;
- не делать commit.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_ownership.py -q
- APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_steam_integration.py tests/test_web_smoke.py tests/test_ownership.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- owner policy chosen
- files changed
- tests added
- safe checks results
- production DB touched yes/no
- import/Steam/parser jobs run yes/no
- remaining risks
- can proceed to Stage 2 review-only yes/no
```

---

# 11. Review-only prompt for Codex

После implementation обязательно запустить отдельный review-only pass:

```text
Проведи review-only проверку Stage 2 Ownership / enforced single-user boundaries.

Ничего не меняй в коде, тестах и документации, кроме создания review-отчёта:
docs/audit/STAGE_2_OWNERSHIP_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к Stage 3.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_MILESTONE.md
- docs/SECURITY.md
- docs/STEAM_IMPORT.md
- docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
- docs/audit/API_SECURITY_INVENTORY.md
- docs/audit/STAGE_2_OWNERSHIP_IMPLEMENTATION_REPORT.md
- текущий git diff, включая untracked files

Проверь Stage 2 DoD:
1. owner policy clearly documented;
2. first user registration works as intended;
3. second user registration blocked or controlled;
4. blocked second registration does not create user;
5. public OpenID callback cannot create uncontrolled second user;
6. callback with owner session links only to owner;
7. API token semantics are owner/operator and documented;
8. dangerous jobs remain protected;
9. Stage 1 security behavior still passes;
10. production DB SHA unchanged unless explicitly allowed;
11. import/Steam/parser production jobs not run;
12. safe pytest passed;
13. ruff passed;
14. git diff --check passed.

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_ownership.py -q
- APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_steam_integration.py tests/test_web_smoke.py tests/test_ownership.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_2_OWNERSHIP_REVIEW.md:

# Stage 2 Ownership Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 3

## Can Proceed To Stage 3
yes/no

Если Stage 2 не проходит — не исправляй, только напиши, что именно не проходит.
```

---

# 12. Commit after review

После review `PASS` или `PASS_WITH_WARNINGS` без blockers:

```bash
git status --short
git --no-pager diff --stat
```

Если нет runtime data / `.env` / `data/*.db`:

```bash
git add app docs tests .env.example
git commit -m "Add enforced single-owner boundaries"
```

Потом:

```bash
git status --short
git log --oneline -5
```

---

# 13. What Stage 3 will be

После Stage 2 следующий этап:

```text
Stage 3: Migration discipline
```

Но Stage 3 не начинать, пока Stage 2 не прошёл:

```text
implementation → review-only → repair if needed → commit
```

