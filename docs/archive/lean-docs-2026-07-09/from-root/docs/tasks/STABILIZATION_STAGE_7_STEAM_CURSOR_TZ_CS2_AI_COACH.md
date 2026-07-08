# CS2 AI Coach — Stabilization Stage 7 / Steam Cursor Truth TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 7 после закрытия Stage 6 Parser facts & confidence hardening.  
Фокус: сделать Steam import cursor/sync behavior детерминированным, безопасным и честно документированным без live Steam jobs и без schema changes.

---

# 1. Статус перед Stage 7

Stage 7 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership / enforced single-owner boundaries committed
[✓] Stage 3 Migration discipline committed
[✓] Stage 4 Recommendation read/write split committed
[✓] Stage 5 Metric Truth Layer committed
[✓] Stage 6 Parser facts & confidence hardening committed
[✓] git push completed
[✓] git status clean
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -10
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой — Stage 7 не начинать.

---

# 2. Главная проблема Stage 7

По full audit и предыдущим этапам в Steam import остаются риски:

```text
- latest share code cursor partially implemented;
- residual knowncode=0 ambiguity;
- unclear source of truth for "latest imported match";
- retry/backoff/durable sync policy weak or undocumented;
- Steam/OpenID/linking уже защищены Stage 1/2, но sync truth ещё не стабилизирован;
- dangerous jobs теперь behind auth, но import behavior должен быть deterministic.
```

Steam import не должен пропускать матчи, плодить дубли, откатываться на старые share codes или путать "нет новых матчей" с ошибкой Steam/API.

---

# 3. Главная цель Stage 7

Ввести явную модель Steam cursor truth без production Steam jobs:

```text
Steam sync должен иметь понятный source of truth:
- какой share code / match считается latest;
- когда cursor обновляется;
- когда cursor НЕ обновляется;
- как обрабатывается knowncode=0;
- как отличать no-new-matches от error;
- как избежать duplicate imports;
- как retry/backoff documented.
```

После Stage 7:

```text
[ ] Steam cursor behavior documented
[ ] mocked tests cover new/no/duplicate/error scenarios
[ ] no live Steam calls in tests
[ ] no production DB mutation
[ ] no production Steam/import/parser jobs
[ ] no schema changes unless explicitly BLOCKED
```

---

# 4. Жёсткие ограничения Stage 7

Запрещено:

```text
- менять DB schema;
- добавлять таблицы/колонки/индексы/constraints;
- делать migrations;
- запускать live Steam API calls;
- запускать production Steam/import/parser jobs;
- делать parser hardening;
- делать AI validator;
- делать recommendation planner;
- делать UI redesign;
- делать friends/SaaS features;
- менять production DB без explicit approval;
- делать commit.
```

Если Codex считает, что Stage 7 невозможно сделать без новой таблицы/колонки для durable cursor ledger, он должен остановиться:

```text
BLOCKED: Stage 7 requires schema change for durable Steam cursor ledger
```

---

# 5. Preferred approach

Предпочтительно сделать Stage 7 как code/docs/tests hardening без schema changes.

## Option A — existing schema is enough

Если в текущей схеме уже есть поля/таблицы для Steam account/latest share code/job state:

```text
- определить source of truth на базе существующих полей;
- убрать/изолировать ambiguous knowncode=0 behavior;
- сделать pure/helper functions для cursor transition;
- добавить mocked tests;
- обновить docs.
```

## Option B — schema needed

Если существующая схема недостаточна:

```text
- не делать schema changes;
- создать inventory + BLOCKED/PASS_WITH_WARNINGS;
- документировать exact migration need for later Stage 7B;
- не мутировать production DB.
```

Stage 7 может быть `PASS_WITH_WARNINGS`, если deterministic behavior улучшен в рамках existing schema, но durable ledger остаётся future work.

---

# 6. Scope Stage 7

## 6.1. Inventory Steam import/cursor state

Найти Steam-related code:

```bash
rg -n "steam|sharecode|share code|knowncode|cursor|latest|sync|import|retry|backoff|match_history|Game Auth|auth code|SteamAccount|ImportJob" app tests docs
```

Создать:

```text
docs/audit/STEAM_CURSOR_INVENTORY.md
```

Inventory должен зафиксировать:

```text
- где хранится Steam account/auth code;
- где хранится latest/current share code;
- где используется knowncode=0;
- какие endpoints/jobs запускают Steam import;
- когда recommendations/evaluations запускаются после import;
- какие retry/error states есть;
- какие gaps остаются.
```

## 6.2. Cursor source of truth

Определить policy:

```text
- latest imported match source;
- latest share code source;
- when cursor advances;
- when cursor does not advance;
- how duplicate match/share code is handled;
- how "no new match" is represented;
- how Steam error is represented.
```

Acceptance:

```text
[ ] source of truth documented in docs/STEAM_IMPORT.md
[ ] no ambiguous knowncode=0 as hidden magic unless documented as initial sentinel
[ ] cursor does not advance on failed import
[ ] duplicate imports do not corrupt state
```

## 6.3. knowncode=0 behavior

Acceptance:

```text
[ ] knowncode=0 is removed from runtime decision-making or explicitly treated as initial sentinel only
[ ] docs explain behavior
[ ] tests cover initial/no-cursor case
```

## 6.4. Retry/backoff/error semantics

Без live jobs:

```text
[ ] define retry/backoff policy in docs;
[ ] add pure/helper behavior if currently possible;
[ ] tests use mocked Steam responses;
[ ] no live Steam calls.
```

Minimum semantics:

```text
SUCCESS_NEW_MATCH_IMPORTED
SUCCESS_NO_NEW_MATCHES
DUPLICATE_ALREADY_IMPORTED
STEAM_TEMPORARY_ERROR
STEAM_AUTH_ERROR
PARSE_OR_IMPORT_ERROR
```

Имена могут отличаться. Важен смысл.

## 6.5. Tests

Добавить/обновить:

```text
tests/test_steam_cursor_truth.py
```

Минимум:

```text
[ ] initial cursor / no latest share code handled deterministically
[ ] successful new match advances cursor only after import success
[ ] failed Steam response does not advance cursor
[ ] duplicate match/share code does not create duplicate import state
[ ] no-new-matches is not treated as failure
[ ] knowncode=0 behavior is explicit
[ ] tests are mocked; no live Steam calls
[ ] no production DB used
[ ] existing Steam/security/ownership tests still pass
```

## 6.6. Docs update

Обновить:

```text
docs/STEAM_IMPORT.md
docs/SECURITY.md если API/job semantics changed
docs/CURRENT_MILESTONE.md
docs/CURRENT_STATUS.md
docs/PROJECT_CONTROL.md
docs/ROADMAP.md
docs/TESTING.md если добавлен test file
docs/CHANGELOG.md
```

Создать:

```text
docs/audit/STEAM_CURSOR_INVENTORY.md
docs/audit/STAGE_7_STEAM_CURSOR_IMPLEMENTATION_REPORT.md
```

---

# 7. Safe checks

Запускать:

```bash
APP_ENV=test .venv/bin/pytest tests/test_steam_cursor_truth.py -q
APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_security.py tests/test_ownership.py tests/test_steam_cursor_truth.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Запрещено запускать:

```text
live Steam API calls
production Steam sync jobs
production import/parser jobs
production demo parsing
production DB mutation
live AI provider jobs
```

---

# 8. Production DB safety

Stage 7 должен сохранить production DB SHA unchanged.

Known hash before Stage 7:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Если SHA меняется без explicit approval — Stage 7 FAIL/BLOCKED.

---

# 9. Stage 7 DoD

Stage 7 считается реализованным только если:

```text
[ ] Steam cursor inventory created
[ ] source of truth documented
[ ] knowncode=0 behavior explicit
[ ] cursor advance rules documented/tested
[ ] failure/no-new/duplicate semantics documented/tested
[ ] mocked tests added
[ ] no live Steam calls
[ ] no production Steam/import/parser jobs
[ ] no production DB mutation
[ ] no schema changes
[ ] Stage 1 security behavior still passes
[ ] Stage 2 ownership behavior still passes
[ ] full pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] implementation report created
```

---

# 10. Implementation prompt for Codex

```text
Начни Stage 7: Steam cursor truth.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_7_STEAM_CURSOR_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/STEAM_IMPORT.md
- docs/SECURITY.md
- docs/TESTING.md
- docs/MIGRATIONS.md
- docs/audit/API_SECURITY_INVENTORY.md
- docs/audit/STAGE_2_OWNERSHIP_REVIEW.md
- docs/audit/STAGE_3_MIGRATION_REVIEW.md
- docs/audit/STAGE_6_PARSER_HARDENING_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_7_STEAM_CURSOR_TZ_CS2_AI_COACH.md

Stage 0 Safety Foundation завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.
Stage 2 Ownership / enforced single-owner boundaries завершён и закоммичен.
Stage 3 Migration discipline завершён и закоммичен.
Stage 4 Recommendation read/write split завершён и закоммичен.
Stage 5 Metric Truth Layer завершён и закоммичен.
Stage 6 Parser facts & confidence hardening завершён и закоммичен.
Git push выполнен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -10
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 7:
сделать Steam import cursor/sync behavior детерминированным и честно документированным без live Steam jobs, без production DB mutation и без schema changes.

Жёсткие ограничения:
- не менять DB schema;
- не добавлять таблицы/колонки/индексы/constraints;
- не делать migrations;
- не запускать live Steam API calls;
- не запускать production Steam/import/parser jobs;
- не делать parser hardening;
- не делать AI validator;
- не делать recommendation planner;
- не делать UI redesign;
- не менять production DB без explicit approval;
- не делать commit.

Нужно:
1. провести inventory Steam import/cursor behavior;
2. создать docs/audit/STEAM_CURSOR_INVENTORY.md;
3. определить source of truth для latest share code / cursor;
4. сделать knowncode=0 behavior explicit;
5. определить when cursor advances / does not advance;
6. определить duplicate/no-new/error semantics;
7. добавить tests/test_steam_cursor_truth.py with mocked Steam paths only;
8. обновить docs/STEAM_IMPORT.md, docs/CURRENT_MILESTONE.md, docs/CURRENT_STATUS.md, docs/PROJECT_CONTROL.md, docs/CHANGELOG.md, docs/TESTING.md;
9. создать docs/audit/STAGE_7_STEAM_CURSOR_IMPLEMENTATION_REPORT.md.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_steam_cursor_truth.py -q
- APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_security.py tests/test_ownership.py tests/test_steam_cursor_truth.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- Steam cursor approach chosen
- files changed
- tests added
- safe checks results
- production DB touched: yes/no
- DB SHA before/after
- live Steam/API jobs run: yes/no
- import/parser jobs run: yes/no
- schema changes: yes/no
- remaining risks
- can proceed to Stage 7 review-only: yes/no

Если считаешь, что для Stage 7 нужны schema changes or live Steam calls — остановись и напиши BLOCKED.
```

---

# 11. Review-only prompt for Codex

После implementation обязательно отдельный review-only pass:

```text
Проведи review-only проверку Stage 7 Steam cursor truth.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_7_STEAM_CURSOR_REVIEW.md

Не запускай live Steam calls.
Не запускай import/Steam/parser production jobs.
Не делай commit.
Не переходи к Stage 8.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/STEAM_IMPORT.md
- docs/SECURITY.md
- docs/TESTING.md
- docs/MIGRATIONS.md
- docs/audit/STEAM_CURSOR_INVENTORY.md
- docs/audit/STAGE_7_STEAM_CURSOR_IMPLEMENTATION_REPORT.md
- docs/tasks/STABILIZATION_STAGE_7_STEAM_CURSOR_TZ_CS2_AI_COACH.md
- текущий git diff, включая untracked files

Проверь Stage 7 DoD:
1. Steam cursor inventory exists and is accurate;
2. source of truth documented;
3. knowncode=0 behavior explicit;
4. cursor advance rules documented/tested;
5. failed Steam response does not advance cursor;
6. duplicate/no-new semantics documented/tested;
7. tests are mocked and do not perform live Steam calls;
8. no production Steam/import/parser jobs run;
9. no production DB mutation;
10. no schema changes;
11. Stage 1 security behavior still passes;
12. Stage 2 ownership behavior still passes;
13. full safe pytest passes;
14. ruff passes;
15. git diff --check passes;
16. no parser hardening;
17. no AI validator;
18. no recommendation planner;
19. no UI redesign.

Особо проверь:
- Steam-related service modules changed
- tests/test_steam_cursor_truth.py
- docs/STEAM_IMPORT.md
- docs/audit/STEAM_CURSOR_INVENTORY.md
- docs/audit/STAGE_7_STEAM_CURSOR_IMPLEMENTATION_REPORT.md

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_steam_cursor_truth.py -q
- APP_ENV=test .venv/bin/pytest tests/test_steam_integration.py tests/test_security.py tests/test_ownership.py tests/test_steam_cursor_truth.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_7_STEAM_CURSOR_REVIEW.md:

# Stage 7 Steam Cursor Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Cursor Truth Review

Отдельно ответь:
- what is the source of truth;
- when cursor advances;
- when cursor does not advance;
- how duplicate/no-new/error cases behave;
- whether knowncode=0 remains ambiguous.

## Live Steam / Job Safety Review

Отдельно ответь:
- were any live Steam calls made;
- were any production Steam/import/parser jobs run;
- do tests use only mocked paths.

## Schema Change Review

Отдельно ответь:
- были ли schema changes;
- если нет, подтвердить;
- если да, Stage 7 FAIL unless explicit approved migration path exists.

## Scope Creep Review

Отдельно ответь:
- был ли parser hardening;
- был ли AI validator;
- был ли recommendation planner;
- был ли UI redesign.

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 8

## Can Proceed To Stage 8
yes/no

Если Stage 7 не проходит — не исправляй, только напиши, что именно не проходит.
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
git add app docs tests
git commit -m "Add Steam cursor truth"
```

После commit:

```bash
git status --short
git log --oneline -10
```

---

# 13. Next stage

После Stage 7:

```text
Stage 8: AI validator
```

Stage 8 не начинать без:

```text
Stage 7 implementation → review-only → repair if needed → commit
```

