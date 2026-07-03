# CS2 AI Coach — Stabilization Stage 6 / Parser Facts & Confidence Hardening TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 6 после закрытия Stage 5 Metric Truth Layer.  
Фокус: улучшить честность parser facts и propagation confidence, не превращая этап в viewer/heatmap/AI/UI/Steam rewrite.

---

# 1. Статус перед Stage 6

Stage 6 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership / enforced single-owner boundaries committed
[✓] Stage 3 Migration discipline committed
[✓] Stage 4 Recommendation read/write split committed
[✓] Stage 5 Metric Truth Layer committed
[✓] git status clean
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -9
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой — Stage 6 не начинать.

---

# 2. Главная проблема Stage 6

После Stage 5 в проекте появился Metric Truth Layer, но часть parser-derived facts всё ещё слабая:

```text
- early_deaths может быть fallback/approximation;
- side split/team inference низкой уверенности;
- traded_deaths / untraded_deaths отсутствуют или unreliable;
- KAST trade component может быть неполным;
- utility attribution и flash facts могут быть approximate;
- parser confidence не всегда доходит до metric truth / recommendations / AI payload;
- некоторые метрики отображаются или используются так, будто они точнее, чем есть.
```

Stage 6 должен не “сделать идеальный парсер”, а сделать parser facts честнее и лучше связать их с Metric Truth Layer.

---

# 3. Главная цель Stage 6

Улучшить parser facts and confidence propagation без schema changes и без production parser jobs.

После Stage 6:

```text
1. parser-derived facts inventory должен быть понятен;
2. weak/fallback parser facts должны быть явно маркированы;
3. Metric Truth Layer должен получать улучшенные confidence/limitations там, где это возможно;
4. early_deaths / side splits / trade-related facts должны быть либо улучшены, либо честно оставлены suppressed/approximate;
5. tests должны доказывать, что слабые parser facts не становятся hard diagnosis/recommendation signals.
```

---

# 4. Жёсткие ограничения Stage 6

Запрещено:

- менять DB schema;
- добавлять таблицы/колонки/индексы/constraints;
- делать migrations;
- запускать production parser jobs;
- запускать production Steam/import jobs;
- перепарсивать production demo files;
- делать viewer/heatmaps/clips;
- делать Steam cursor truth;
- делать AI validator;
- делать recommendation planner;
- делать UI redesign;
- менять production DB без explicit approval;
- делать commit.

Если Codex считает, что для Stage 6 нужна новая таблица/поле — он должен остановиться и написать:

```text
BLOCKED: Stage 6 requires schema change
```

а не импровизировать.

---

# 5. Preferred approach

Stage 6 должен быть focused parser-confidence hardening:

```text
- inventory;
- small parser fact fixes if safe;
- confidence metadata;
- Metric Truth registry reliability updates;
- tests with existing fixtures/mocked parser outputs;
- no production parsing.
```

Допустимые изменения:

```text
app/services/demo_parser*
app/services/parser*
app/services/metric_truth.py
app/services/recommendation_tracking.py only if consuming confidence metadata
tests/parser-related tests
docs/METRICS.md
docs/audit/PARSER_FACTS_INVENTORY.md
```

Но только если изменения не создают новые schema requirements.

---

# 6. Scope Stage 6

## 6.1. Inventory parser facts

Найти parser/fact surfaces:

```bash
rg -n "parser|demoparser|parse|demo|early_death|entry_death|trade|traded|side|team|confidence|kast|flash|utility|damage" app tests docs
```

Создать:

```text
docs/audit/PARSER_FACTS_INVENTORY.md
```

Inventory должен зафиксировать:

- какие parser-derived facts есть;
- где они считаются;
- где confidence уже есть;
- какие facts используются в metrics/recommendations/AI payload;
- какие facts trusted/medium/approximate/low/unavailable;
- какие gaps остаются for later deep parser work.

## 6.2. Early deaths

Проверить текущую реализацию:

```text
early_deaths
entry_deaths
first_death / first victim / time threshold
round events timing
```

Acceptance:

```text
[ ] no silent fallback early_deaths = entry_deaths in hard recommendation logic
[ ] if actual timing cannot be reliably derived, early_deaths stays approximate/warn-only
[ ] docs explain limitation
[ ] tests cover missing/approximate early_deaths behavior
```

Если можно безопасно улучшить early death timing from existing parsed events/fixtures — сделать.  
Если нельзя — не выдумывать, честно оставить approximate.

## 6.3. Trade / traded death facts

Проверить:

```text
trade_kills
traded_deaths
untraded_deaths
KAST trade component
```

Acceptance:

```text
[ ] trade_kills reliability remains low/medium according to actual parser support
[ ] traded_deaths remains unavailable/suppressed unless truly implemented
[ ] no recommendation hard-claim from unavailable traded_deaths
[ ] docs explain what is missing
```

Не реализовывать сложный full trade graph, если для этого нужны новые structures/schema/large parser rewrite.

## 6.4. Side split / team inference

Проверить:

```text
T/CT side stats
team switching
player side inference
round side attribution
```

Acceptance:

```text
[ ] side_split_metrics reliability remains low unless confidence is proven
[ ] Metric Truth Layer reflects parser confidence
[ ] docs explain low-confidence side split limitation
```

## 6.5. Utility / flash facts

Проверить:

```text
utility_damage
flash_assists
enemies_flashed
grenade_rating
```

Acceptance:

```text
[ ] utility_damage confidence documented
[ ] flash facts marked approximate if attribution incomplete
[ ] grenade_rating remains unavailable unless actually implemented
```

## 6.6. Integration with Metric Truth Layer

Stage 6 should update Metric Truth only when parser evidence changes.

Examples:

```text
- if early_deaths remains approximate, keep approximate/warn-only;
- if side split still weak, keep low/suppressed;
- if traded_deaths still missing, keep unavailable;
- if utility_damage is reasonably parser-backed, medium is acceptable with limitations.
```

No false upgrades.

## 6.7. Tests

Добавить/обновить:

```text
tests/test_parser_facts_confidence.py
```

Минимум:

1. early_deaths missing/fallback does not become trusted hard signal.
2. side_split_metrics remains low/suppressed unless confidence provided.
3. traded_deaths unavailable is suppressed for diagnosis/recommendation.
4. utility/flash facts keep appropriate reliability/warnings.
5. Metric Truth registry reflects parser confidence limitations.
6. no production demo parsing required.
7. no DB schema access required unless using temp DB fixtures.
8. existing metric truth tests still pass.

Если есть existing parser fixture tests — обновить их минимально.

---

# 7. Docs update

Обновить:

```text
docs/METRICS.md
docs/RECOMMENDATIONS.md если recommendation hard signals changed
docs/AI_COACH.md если AI payload limitations changed
docs/CURRENT_MILESTONE.md
docs/CURRENT_STATUS.md
docs/PROJECT_CONTROL.md
docs/ROADMAP.md
docs/TESTING.md если добавлен test file
docs/CHANGELOG.md
```

Создать:

```text
docs/audit/PARSER_FACTS_INVENTORY.md
docs/audit/STAGE_6_PARSER_HARDENING_IMPLEMENTATION_REPORT.md
```

---

# 8. Safe checks

Запускать:

```bash
APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Запрещено запускать:

```text
production parser jobs
production Steam/import jobs
live demo parsing over data/incoming_demos
production DB mutation
live AI provider jobs
```

---

# 9. Production DB safety

Stage 6 должен сохранить production DB SHA unchanged.

Known hash before Stage 6:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Если SHA меняется без explicit approval — Stage 6 FAIL/BLOCKED.

---

# 10. Stage 6 DoD

Stage 6 считается реализованным только если:

```text
[ ] parser facts inventory created
[ ] parser confidence limitations documented
[ ] early_deaths behavior is either improved or clearly approximate/warn-only
[ ] side split limitations remain honest
[ ] traded_deaths/untraded_deaths not falsely treated as available
[ ] utility/flash facts reliability documented
[ ] Metric Truth Layer updated only where evidence supports it
[ ] tests cover parser fact confidence behavior
[ ] no DB schema changes
[ ] no production DB mutation
[ ] no production parser/Steam/import jobs
[ ] no viewer/heatmaps/clips
[ ] no Steam cursor work
[ ] no AI validator
[ ] no recommendation planner
[ ] full pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] implementation report created
```

---

# 11. Implementation prompt for Codex

```text
Начни Stage 6: Parser facts & confidence hardening.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_6_PARSER_HARDENING_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/AI_COACH.md
- docs/MIGRATIONS.md
- docs/audit/METRIC_TRUTH_INVENTORY.md
- docs/audit/STAGE_5_METRIC_TRUTH_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_6_PARSER_HARDENING_TZ_CS2_AI_COACH.md

Stage 0 Safety Foundation завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.
Stage 2 Ownership / enforced single-owner boundaries завершён и закоммичен.
Stage 3 Migration discipline завершён и закоммичен.
Stage 4 Recommendation read/write split завершён и закоммичен.
Stage 5 Metric Truth Layer завершён и закоммичен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -9
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 6:
улучшить parser-derived facts/confidence и связать ограничения parser facts с Metric Truth Layer без schema changes и без production parser jobs.

Жёсткие ограничения:
- не менять DB schema;
- не добавлять таблицы/колонки/индексы/constraints;
- не делать migrations;
- не запускать production parser jobs;
- не запускать production Steam/import jobs;
- не перепарсивать production demo files;
- не делать viewer/heatmaps/clips;
- не делать Steam cursor truth;
- не делать AI validator;
- не делать recommendation planner;
- не делать UI redesign;
- не менять production DB без explicit approval;
- не делать commit.

Нужно:
1. провести inventory parser facts;
2. создать docs/audit/PARSER_FACTS_INVENTORY.md;
3. проверить early_deaths/entry_deaths behavior:
   - улучшить только если это safe and supported by existing facts;
   - иначе оставить approximate/warn-only and documented;
4. проверить trade_kills/traded_deaths/untraded_deaths/KAST trade component limitations;
5. проверить side split/team inference confidence;
6. проверить utility/flash facts reliability;
7. обновить Metric Truth Layer only where parser evidence supports it;
8. добавить tests/test_parser_facts_confidence.py;
9. обновить docs/METRICS.md, docs/RECOMMENDATIONS.md, docs/AI_COACH.md при необходимости, docs/CURRENT_MILESTONE.md, docs/CURRENT_STATUS.md, docs/PROJECT_CONTROL.md, docs/CHANGELOG.md;
10. создать docs/audit/STAGE_6_PARSER_HARDENING_IMPLEMENTATION_REPORT.md.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
- APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- parser hardening approach chosen
- files changed
- tests added
- safe checks results
- production DB touched: yes/no
- DB SHA before/after
- production parser/Steam/import jobs run: yes/no
- schema changes: yes/no
- remaining risks
- can proceed to Stage 6 review-only: yes/no

Если считаешь, что для Stage 6 нужны schema changes or production parsing — остановись и напиши BLOCKED.
```

---

# 12. Review-only prompt for Codex

После implementation обязательно отдельный review-only pass:

```text
Проведи review-only проверку Stage 6 Parser facts & confidence hardening.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_6_PARSER_HARDENING_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к Stage 7.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/AI_COACH.md
- docs/MIGRATIONS.md
- docs/audit/PARSER_FACTS_INVENTORY.md
- docs/audit/STAGE_6_PARSER_HARDENING_IMPLEMENTATION_REPORT.md
- docs/tasks/STABILIZATION_STAGE_6_PARSER_HARDENING_TZ_CS2_AI_COACH.md
- текущий git diff, включая untracked files

Проверь Stage 6 DoD:
1. parser facts inventory exists and is accurate;
2. parser confidence limitations documented;
3. early_deaths behavior is honest and not falsely trusted;
4. no silent early_deaths=entry_deaths hard claim;
5. side split limitations remain honest;
6. traded_deaths/untraded_deaths not falsely treated as available;
7. utility/flash facts reliability documented;
8. Metric Truth Layer updated only where evidence supports it;
9. tests cover parser fact confidence behavior;
10. no DB schema changes;
11. production DB SHA unchanged;
12. no production parser/Steam/import jobs run;
13. full safe pytest passes;
14. ruff passes;
15. git diff --check passes;
16. no viewer/heatmaps/clips;
17. no Steam cursor work;
18. no AI validator;
19. no recommendation planner;
20. no UI redesign.

Особо проверь:
- parser-related service modules changed
- app/services/metric_truth.py
- app/services/recommendation_tracking.py if changed
- tests/test_parser_facts_confidence.py
- docs/audit/PARSER_FACTS_INVENTORY.md
- docs/audit/STAGE_6_PARSER_HARDENING_IMPLEMENTATION_REPORT.md

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_parser_facts_confidence.py -q
- APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_parser_facts_confidence.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_6_PARSER_HARDENING_REVIEW.md:

# Stage 6 Parser Hardening Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Parser Facts Review

Отдельно ответь:
- какие parser facts improved;
- какие остались approximate/low/unavailable;
- какие facts suppressed from hard diagnosis/recommendation;
- не появились ли claims stronger than evidence.

## Metric Truth Integration Review

Отдельно ответь:
- какие metric reliability изменены;
- почему evidence достаточно;
- какие reliability не повышались intentionally.

## Schema Change Review

Отдельно ответь:
- были ли schema changes;
- если нет, подтвердить;
- если да, Stage 6 FAIL unless explicit approved migration path exists.

## Scope Creep Review

Отдельно ответь:
- был ли viewer/heatmap/clip work;
- был ли Steam cursor work;
- был ли AI validator;
- был ли recommendation planner;
- был ли UI redesign.

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 7

## Can Proceed To Stage 7
yes/no

Если Stage 6 не проходит — не исправляй, только напиши, что именно не проходит.
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
git commit -m "Harden parser fact confidence"
```

После commit:

```bash
git status --short
git log --oneline -9
```

---

# 14. Next stage

После Stage 6:

```text
Stage 7: Steam cursor truth
```

Stage 7 не начинать без:

```text
Stage 6 implementation → review-only → repair if needed → commit

