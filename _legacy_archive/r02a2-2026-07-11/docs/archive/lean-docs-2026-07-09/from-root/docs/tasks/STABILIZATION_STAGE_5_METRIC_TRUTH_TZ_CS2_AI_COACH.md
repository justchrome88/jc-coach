# CS2 AI Coach — Stabilization Stage 5 / Metric Truth Layer TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 5 после закрытия Stage 4 Recommendation read/write split.  
Фокус: ввести слой правды по метрикам — какие метрики точные, какие approximate, какие нельзя использовать для диагноза/AI/recommendations без предупреждений.

---

# 1. Статус перед Stage 5

Stage 5 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership / enforced single-owner boundaries committed
[✓] Stage 3 Migration discipline committed
[✓] Stage 4 Recommendation read/write split committed
[✓] git status clean
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -8
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой — Stage 5 не начинать.

---

# 2. Главная проблема Stage 5

По full audit в проекте есть проблема metric trust:

```text
- много метрик уже есть;
- но нет единого registry/source/formula/reliability/suppression layer;
- часть метрик является fallback/approximation;
- early_deaths может быть равно entry_deaths;
- side split confidence низкий;
- trade_kill есть, но traded/untraded death может отсутствовать;
- parser confidence не всегда управляет diagnosis/recommendation;
- AI/coach может воспринимать слабые метрики как точные.
```

Это опасно, потому что AI Coach не должен делать уверенные выводы на слабых или приблизительных данных.

---

# 3. Главная цель Stage 5

Ввести Metric Truth Layer без schema changes:

```text
каждая важная метрика должна иметь:
- stable metric id;
- display name;
- source;
- formula/definition;
- reliability level;
- confidence/suppression rules;
- known limitations;
- allowed usage: display / diagnosis / recommendation / AI.
```

После Stage 5 система должна уметь:

```text
1. отличать trusted metric от approximate metric;
2. не использовать unreliable metric для жёсткого диагноза без warning;
3. отдавать diagnosis/recommendation/AI layer metadata о надёжности;
4. показывать в docs честные ограничения;
5. тестировать suppression/reliability behavior.
```

---

# 4. Жёсткие ограничения Stage 5

Запрещено:

- менять DB schema;
- добавлять таблицы/колонки/индексы/constraints;
- делать migrations;
- менять parser facts глубоко;
- менять Steam import/cursor;
- делать AI validator;
- делать recommendation planner;
- делать UI redesign;
- запускать production import/Steam/parser jobs;
- менять production DB без explicit approval;
- делать commit.

Если Codex считает, что для Stage 5 нужна новая таблица/поле — он должен остановиться и написать:

```text
BLOCKED: Stage 5 requires schema change
```

а не импровизировать.

---

# 5. Предпочтительный подход

Stage 5 должен быть code/config/docs layer, не DB layer.

Допустимая реализация:

```text
app/services/metric_truth.py
app/services/metric_registry.py
или аналогичный модуль
```

Модель может быть dataclass/TypedDict/Pydantic, если уже используется.

Пример сущностей:

```text
MetricReliability:
- trusted
- medium
- approximate
- low
- unavailable

MetricUsage:
- display_allowed
- diagnosis_allowed
- recommendation_allowed
- ai_allowed

MetricDefinition:
- id
- name
- description
- source
- formula
- reliability
- limitations
- suppress_if
- requires_parser_confidence
```

Не обязательно использовать ровно эти имена. Важен смысл.

---

# 6. Scope Stage 5

## 6.1. Inventory current metrics

Найти текущие метрики:

```bash
rg -n "ADR|KAST|HLTV|rating|entry|death|trade|headshot|aim|utility|grenade|round|metric|score|confidence|side|ct|t_" app tests docs
```

Создать:

```text
docs/audit/METRIC_TRUTH_INVENTORY.md
```

Inventory должен зафиксировать:

- какие метрики есть;
- где считаются;
- откуда берутся;
- какие reliable;
- какие approximate/fallback;
- какие не должны использоваться для строгого диагноза;
- какие надо перенести в later parser hardening.

## 6.2. Implement Metric Truth Layer

Добавить модуль, который умеет:

```text
- регистрировать known metrics;
- отдавать definition by metric id;
- отдавать reliability;
- проверять allowed usage;
- возвращать suppression/warnings для слабых метрик.
```

Минимальный набор метрик для registry:

```text
adr
kast
hltv_rating
kills_per_round
deaths_per_round
kd_ratio
headshot_rate
entry_deaths
early_deaths
trade_kills
utility_damage
grenade_rating
aim_rating
side_split_metrics
```

Если фактические ids в проекте отличаются — использовать существующие.

## 6.3. Connect to diagnosis/recommendation without planner

Не делать новый planner.

Но если текущая recommendation/diagnosis логика использует метрики, нужно минимально подключить truth layer:

```text
- read reliability metadata;
- avoid hard recommendation when metric is suppressed/unreliable;
- include warning/limitation where existing output already supports it;
- no DB changes.
```

Если текущая логика не имеет clean integration point — зафиксировать in report as PASS_WITH_WARNINGS, но tests должны покрывать metric truth module itself.

## 6.4. Docs

Обновить:

```text
docs/METRICS.md
docs/RECOMMENDATIONS.md
docs/AI_COACH.md если AI input mentions metrics
docs/CURRENT_MILESTONE.md
docs/CURRENT_STATUS.md
docs/PROJECT_CONTROL.md
docs/ROADMAP.md
docs/TESTING.md если добавлен test file
docs/CHANGELOG.md
```

Создать:

```text
docs/audit/METRIC_TRUTH_INVENTORY.md
docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md
```

---

# 7. Tests to add/update

Добавить:

```text
tests/test_metric_truth.py
```

Минимум:

1. Registry contains required core metrics.
2. Trusted metric can be used for display/diagnosis/recommendation/AI according to policy.
3. Approximate metric is marked approximate and includes limitations.
4. Low/unavailable metric is suppressed from hard diagnosis/recommendation.
5. `early_deaths` is not treated as fully trusted if it falls back to entry deaths.
6. side split metrics are marked low/approximate unless confidence is available.
7. unknown metric id returns safe unavailable/blocked behavior.
8. no DB/schema access required for metric truth tests.

Если подключаешь к recommendation/diagnosis:

9. recommendation/diagnosis does not make hard claim from suppressed metric.
10. output contains warning/limitation for approximate metric.

---

# 8. Safe checks

Запускать:

```bash
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
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
live AI provider jobs
production DB mutation
```

---

# 9. Production DB safety

Stage 5 должен сохранить production DB SHA unchanged.

Known hash before Stage 5:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Если SHA меняется без explicit approval — Stage 5 FAIL/BLOCKED.

---

# 10. Stage 5 DoD

Stage 5 считается реализованным только если:

```text
[ ] metric truth inventory created
[ ] metric registry/truth layer implemented
[ ] each core metric has source/formula/reliability/limitations
[ ] weak/fallback metrics are not treated as fully trusted
[ ] suppression/usage rules exist
[ ] tests cover trusted/approximate/unavailable behavior
[ ] docs/METRICS.md no longer placeholder
[ ] no DB schema changes
[ ] no production DB mutation
[ ] no import/Steam/parser production jobs
[ ] full pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] implementation report created
```

---

# 11. Implementation prompt for Codex

```text
Начни Stage 5: Metric Truth Layer.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_5_METRIC_TRUTH_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/AI_COACH.md
- docs/MIGRATIONS.md
- docs/audit/STAGE_3_MIGRATION_REVIEW.md
- docs/audit/STAGE_4_RECOMMENDATION_RW_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_5_METRIC_TRUTH_TZ_CS2_AI_COACH.md

Stage 0 Safety Foundation завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.
Stage 2 Ownership / enforced single-owner boundaries завершён и закоммичен.
Stage 3 Migration discipline завершён и закоммичен.
Stage 4 Recommendation read/write split завершён и закоммичен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -8
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 5:
ввести Metric Truth Layer без schema changes, чтобы метрики имели source/formula/reliability/limitations и слабые метрики не использовались как fully trusted.

Жёсткие ограничения:
- не менять DB schema;
- не добавлять таблицы/колонки/индексы/constraints;
- не делать migrations;
- не делать parser hardening;
- не менять Steam import/cursor;
- не делать AI validator;
- не делать recommendation planner;
- не делать UI redesign;
- не запускать import/Steam/parser production jobs;
- не менять production DB без explicit approval;
- не делать commit.

Нужно:
1. провести inventory текущих метрик;
2. создать docs/audit/METRIC_TRUTH_INVENTORY.md;
3. реализовать metric truth/registry module без DB schema changes;
4. классифицировать core metrics по reliability:
   - trusted
   - medium
   - approximate
   - low
   - unavailable
5. добавить usage/suppression policy:
   - display
   - diagnosis
   - recommendation
   - AI
6. явно пометить fallback/weak metrics:
   - early_deaths if fallback-like
   - side split metrics if low confidence
   - trade/traded death limitations
7. добавить tests/test_metric_truth.py;
8. минимально подключить truth layer к existing diagnosis/recommendation code only if there is a clean integration point without planner/schema changes;
9. обновить docs/METRICS.md, docs/RECOMMENDATIONS.md, docs/AI_COACH.md при необходимости, docs/CURRENT_MILESTONE.md, docs/CURRENT_STATUS.md, docs/PROJECT_CONTROL.md, docs/CHANGELOG.md;
10. создать docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
- APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- metric truth approach chosen
- files changed
- tests added
- safe checks results
- production DB touched: yes/no
- DB SHA before/after
- import/Steam/parser jobs run: yes/no
- schema changes: yes/no
- remaining risks
- can proceed to Stage 5 review-only: yes/no

Если считаешь, что для Stage 5 нужны schema changes — остановись и напиши BLOCKED.
```

---

# 12. Review-only prompt for Codex

После implementation обязательно отдельный review-only pass:

```text
Проведи review-only проверку Stage 5 Metric Truth Layer.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_5_METRIC_TRUTH_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к Stage 6.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/AI_COACH.md
- docs/MIGRATIONS.md
- docs/audit/METRIC_TRUTH_INVENTORY.md
- docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md
- docs/tasks/STABILIZATION_STAGE_5_METRIC_TRUTH_TZ_CS2_AI_COACH.md
- текущий git diff, включая untracked files

Проверь Stage 5 DoD:
1. metric truth inventory exists and is accurate;
2. metric registry/truth layer exists;
3. each core metric has source/formula/reliability/limitations;
4. fallback/weak metrics are not fully trusted;
5. early_deaths limitations are explicit;
6. side split reliability limitations are explicit;
7. unknown metric behavior is safe;
8. usage/suppression policy exists for display/diagnosis/recommendation/AI;
9. tests cover trusted/approximate/unavailable behavior;
10. docs/METRICS.md no longer placeholder;
11. no DB schema changes;
12. production DB SHA unchanged;
13. import/Steam/parser production jobs not run;
14. full safe pytest passes;
15. ruff passes;
16. git diff --check passes;
17. no parser hardening / Steam cursor / AI validator / planner / UI scope creep.

Особо проверь:
- metric truth/registry module
- tests/test_metric_truth.py
- docs/METRICS.md
- docs/audit/METRIC_TRUTH_INVENTORY.md
- docs/audit/STAGE_5_METRIC_TRUTH_IMPLEMENTATION_REPORT.md

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py -q
- APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_metric_truth.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_5_METRIC_TRUTH_REVIEW.md:

# Stage 5 Metric Truth Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Metric Truth Review

Отдельно ответь:
- какие metrics trusted;
- какие approximate/low/unavailable;
- какие suppress from hard diagnosis/recommendation;
- есть ли метрики, которые всё ещё выглядят точнее, чем реально являются.

## Schema Change Review

Отдельно ответь:
- были ли schema changes;
- если нет, подтвердить;
- если да, Stage 5 FAIL unless explicit approved migration path exists.

## Scope Creep Review

Отдельно ответь:
- был ли parser hardening;
- был ли Steam cursor work;
- был ли AI validator;
- был ли recommendation planner;
- был ли UI redesign.

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 6

## Can Proceed To Stage 6
yes/no

Если Stage 5 не проходит — не исправляй, только напиши, что именно не проходит.
```

---

# 13. Commit after review

После review `PASS` или `PASS_WITH_WARNINGS` без blockers:

```bash
git status --short
git --no-pager diff --stat
```

Если нет runtime data / `.env` / `data/*.db`:

```bash
git add app docs tests
git commit -m "Add metric truth layer"
```

После commit:

```bash
git status --short
git log --oneline -8
```

---

# 14. Next stage

После Stage 5:

```text
Stage 6: Parser hardening
```

Stage 6 не начинать без:

```text
Stage 5 implementation → review-only → repair if needed → commit

