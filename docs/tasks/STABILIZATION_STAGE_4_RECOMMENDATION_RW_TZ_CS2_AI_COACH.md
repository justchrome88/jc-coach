# CS2 AI Coach — Stabilization Stage 4 / Recommendation Read-Write Split TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 4 после закрытия Stage 3 Migration discipline.  
Фокус: убрать побочные записи из recommendation read paths. GET/read должен читать, POST/command должен мутировать явно.

---

# 1. Статус перед Stage 4

Stage 4 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership / enforced single-owner boundaries committed
[✓] Stage 3 Migration discipline committed
[✓] git push completed
[✓] git status clean
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -7
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой — Stage 4 не начинать.

---

# 2. Главная проблема Stage 4

По audit и API inventory в проекте есть опасный architectural smell:

```text
GET /api/recommendations* can mutate indirectly
recommendation service read helpers can evaluate/create records
```

Это значит, что простое чтение рекомендаций может создавать/изменять записи в БД. Это ломает:

```text
- predictability;
- tests;
- API semantics;
- future planner;
- future Metric Truth Layer;
- future AI validator;
- trust in coach loop.
```

После Stage 4 должно быть жёсткое правило:

```text
Read paths do not write.
Write paths write explicitly.
```

---

# 3. Главная цель Stage 4

Разделить recommendation read и write responsibilities без schema changes:

```text
GET/read/query/helper paths:
  - только читают;
  - не создают recommendations;
  - не создают evaluations;
  - не делают commit/flush/side-effect.

POST/command/job paths:
  - явно выполняют mutation;
  - имеют auth/CSRF/API token protection from Stage 1;
  - проходят owner boundary from Stage 2;
  - остаются в рамках текущей схемы DB.
```

---

# 4. Жёсткие ограничения Stage 4

Запрещено:

- менять DB schema;
- добавлять таблицы;
- добавлять колонки;
- добавлять индексы/constraints;
- делать migrations;
- внедрять полноценный recommendation planner;
- делать Metric Truth Layer;
- менять parser facts;
- менять Steam import/cursor;
- менять AI provider/validator;
- делать UI redesign;
- запускать production import/Steam/parser jobs;
- менять production DB без explicit approval;
- делать commit.

Если Codex считает, что без schema changes нельзя — он должен остановиться и написать:

```text
BLOCKED: Stage 4 requires schema change
```

а не импровизировать.

---

# 5. Scope Stage 4

## 5.1. Inventory recommendation side effects

Найти все recommendation-related read/write paths:

```bash
rg -n "recommend|evaluation|CoachRecommendation|MatchRecommendationEvaluation|commit\\(|flush\\(|add\\(|delete\\(" app tests docs
```

Создать:

```text
docs/audit/RECOMMENDATION_SIDE_EFFECT_INVENTORY.md
```

В inventory зафиксировать:

- API routes;
- web routes;
- services/helpers;
- места, где read-like functions делают `db.add`, `db.commit`, `db.flush`;
- места, где recommendations/evaluations создаются автоматически;
- что исправлено в Stage 4;
- что остаётся later planner work.

## 5.2. Split read/query service and mutation/command service

Нужно найти текущие functions, которые выглядят как read but mutate.

Предпочтительная модель:

```text
read/query functions:
  list_active_recommendations(...)
  get_recommendation(...)
  get_recommendation_evaluations(...)
  build_recommendation_view_model(...)

command/mutation functions:
  ensure_default_recommendations(...)
  evaluate_recommendations_for_match(...)
  update_recommendation_status(...)
  extend_recommendation(...)
  restart_recommendation_category(...)
```

Названия могут отличаться, но смысл должен быть такой.

Acceptance:

```text
[ ] read functions have no db.add/commit/flush/delete
[ ] mutation functions are explicit and named as mutation/command/evaluate/ensure
[ ] routes call the correct layer
```

## 5.3. API behavior

Для `GET /api/recommendations*`:

```text
[ ] should not create recommendations
[ ] should not create evaluations
[ ] should not change status/progress
[ ] should not commit
```

Для POST routes:

```text
[ ] status/extend/restart remain explicitly mutating
[ ] auth/CSRF/token behavior from Stage 1 remains intact
[ ] owner boundary from Stage 2 remains intact
```

## 5.4. Web behavior

Для pages like `/coach`, `/report`, recommendation widgets:

```text
[ ] page rendering should not silently create default recommendations unless route is explicitly documented as init/repair action
[ ] if current UI depends on auto-ensure, move ensure to explicit startup/command path or documented safe initialization path
[ ] do not redesign UI
```

Если полностью убрать auto-ensure ломает текущий UX, допускается временный explicit endpoint/action or controlled startup/init path, но read paths всё равно должны быть side-effect free.

## 5.5. Tests

Добавить/обновить:

```text
tests/test_recommendation_read_write_split.py
```

Минимум тестов:

1. GET/list recommendation API does not change recommendation row count.
2. GET/list recommendation API does not change evaluation row count.
3. Coach/recommendation read helper does not call commit on read.
4. POST status/extend/restart still mutates intentionally.
5. Existing Stage 1 security tests still pass.
6. Existing Stage 2 ownership tests still pass.
7. Full tests pass.

Если DB row-count test требует setup, использовать isolated temp DB from Stage 0.

## 5.6. Docs update

Обновить:

```text
docs/RECOMMENDATIONS.md
docs/SECURITY.md если API semantics changed
docs/CURRENT_MILESTONE.md
docs/CURRENT_STATUS.md
docs/PROJECT_CONTROL.md
docs/ROADMAP.md
docs/TESTING.md если добавлен test file
docs/CHANGELOG.md
```

Создать:

```text
docs/audit/RECOMMENDATION_SIDE_EFFECT_INVENTORY.md
docs/audit/STAGE_4_RECOMMENDATION_RW_IMPLEMENTATION_REPORT.md
```

---

# 6. Safe checks

Запускать:

```bash
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py -q
APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_ownership.py tests/test_recommendation_read_write_split.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Запрещено запускать:

```text
production import
Steam sync
parser jobs
demo parsing jobs
live AI provider jobs unless existing tests mock them
production DB mutation
```

---

# 7. Production DB safety

Stage 4 должен сохранить production DB SHA unchanged.

Known hash before Stage 4:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Если SHA изменился без explicit approval — Stage 4 FAIL/BLOCKED.

---

# 8. Stage 4 DoD

Stage 4 считается реализованным только если:

```text
[ ] recommendation side-effect inventory created
[ ] read/write responsibilities documented
[ ] GET/read recommendation paths do not mutate DB
[ ] read helpers do not add/commit/flush/delete
[ ] explicit mutation commands remain functional
[ ] POST recommendation actions still work
[ ] Stage 1 security behavior still passes
[ ] Stage 2 ownership behavior still passes
[ ] no schema changes
[ ] no production DB mutation
[ ] no import/Steam/parser production jobs
[ ] tests added
[ ] full pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] implementation report created
```

---

# 9. Implementation prompt for Codex

```text
Начни Stage 4: Recommendation read/write split.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_4_RECOMMENDATION_RW_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/RECOMMENDATIONS.md
- docs/SECURITY.md
- docs/TESTING.md
- docs/MIGRATIONS.md
- docs/audit/API_SECURITY_INVENTORY.md
- docs/audit/STAGE_2_OWNERSHIP_REVIEW.md
- docs/audit/STAGE_3_MIGRATION_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_4_RECOMMENDATION_RW_TZ_CS2_AI_COACH.md

Stage 0 Safety Foundation завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.
Stage 2 Ownership / enforced single-owner boundaries завершён и закоммичен.
Stage 3 Migration discipline завершён и закоммичен.
Git push выполнен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -7
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 4:
разделить recommendation read/write behavior так, чтобы GET/read paths больше не мутировали БД.

Жёсткие ограничения:
- не менять DB schema;
- не добавлять таблицы/колонки/индексы/constraints;
- не делать migrations;
- не делать recommendation planner;
- не делать Metric Truth Layer;
- не менять parser/Steam/AI/UI behavior вне минимально нужного;
- не запускать import/Steam/parser production jobs;
- не менять production DB без explicit approval;
- не делать commit.

Нужно:
1. найти все recommendation read/write side effects;
2. создать docs/audit/RECOMMENDATION_SIDE_EFFECT_INVENTORY.md;
3. отделить read/query functions от explicit mutation/command functions;
4. сделать так, чтобы GET /api/recommendations* и read helpers не создавали/не обновляли DB records;
5. сохранить POST status/extend/restart as explicit mutation paths;
6. добавить tests/test_recommendation_read_write_split.py:
   - GET/read не меняет recommendation row count;
   - GET/read не меняет evaluation row count;
   - explicit POST mutation still works;
   - Stage 1/2 protections still pass;
7. обновить docs/RECOMMENDATIONS.md, docs/CURRENT_MILESTONE.md, docs/CURRENT_STATUS.md, docs/PROJECT_CONTROL.md, docs/CHANGELOG.md;
8. создать docs/audit/STAGE_4_RECOMMENDATION_RW_IMPLEMENTATION_REPORT.md.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py -q
- APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_ownership.py tests/test_recommendation_read_write_split.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- recommendation read/write approach chosen
- files changed
- tests added
- safe checks results
- production DB touched: yes/no
- DB SHA before/after
- import/Steam/parser jobs run: yes/no
- schema changes: yes/no
- remaining risks
- can proceed to Stage 4 review-only: yes/no

Если считаешь, что для Stage 4 нужны schema changes — остановись и напиши BLOCKED.
```

---

# 10. Review-only prompt for Codex

После implementation обязательно отдельный review-only pass:

```text
Проведи review-only проверку Stage 4 Recommendation read/write split.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_4_RECOMMENDATION_RW_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к Stage 5.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/RECOMMENDATIONS.md
- docs/MIGRATIONS.md
- docs/audit/RECOMMENDATION_SIDE_EFFECT_INVENTORY.md
- docs/audit/STAGE_4_RECOMMENDATION_RW_IMPLEMENTATION_REPORT.md
- текущий git diff, включая untracked files

Проверь Stage 4 DoD:
1. recommendation side-effect inventory exists and is accurate;
2. GET/read recommendation paths do not mutate DB;
3. read helpers do not add/commit/flush/delete;
4. mutation commands are explicit;
5. POST recommendation actions still work;
6. Stage 1 security tests still pass;
7. Stage 2 ownership tests still pass;
8. no DB schema changes;
9. production DB SHA unchanged;
10. import/Steam/parser production jobs not run;
11. full safe pytest passes;
12. ruff passes;
13. git diff --check passes;
14. no Metric Truth Layer/planner/parser/Steam/AI/UI scope creep.

Особо проверь:
- all app/services/*recommend*
- app/main.py
- app/web/routes.py
- tests/test_recommendation_read_write_split.py
- docs/audit/RECOMMENDATION_SIDE_EFFECT_INVENTORY.md

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py -q
- APP_ENV=test .venv/bin/pytest tests/test_security.py tests/test_ownership.py tests/test_recommendation_read_write_split.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_4_RECOMMENDATION_RW_REVIEW.md:

# Stage 4 Recommendation Read/Write Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Read Path Mutation Review

Отдельно ответь:
- какие GET/read paths раньше могли мутировать;
- какие теперь гарантированно не мутируют;
- есть ли ещё read-like path with side effects;
- является ли это blocker before Stage 5.

## Schema Change Review

Отдельно ответь:
- были ли schema changes;
- если нет, подтвердить;
- если да, Stage 4 FAIL unless explicit approved migration path exists.

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 5

## Can Proceed To Stage 5
yes/no

Если Stage 4 не проходит — не исправляй, только напиши, что именно не проходит.
```

---

# 11. Commit after review

После review `PASS` или `PASS_WITH_WARNINGS` без blockers:

```bash
git status --short
git --no-pager diff --stat
```

Если нет runtime data / `.env` / `data/*.db`:

```bash
git add app docs tests
git commit -m "Split recommendation reads from writes"
```

После commit:

```bash
git status --short
git log --oneline -7
```

---

# 12. Next stage

После Stage 4:

```text
Stage 5: Metric Truth Layer
```

Stage 5 не начинать без:

```text
Stage 4 implementation → review-only → repair if needed → commit

