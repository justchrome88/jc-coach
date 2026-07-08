# CS2 AI Coach — Stabilization Stage 9 / Coach-first UI TZ

Дата: 2026-07-03  
Назначение: Stage 9 после full audit Stage 0–8.  
Фокус: сделать существующий coach loop видимым и удобным без изменения движка, схемы БД и внешних jobs.

---

# 1. Статус перед Stage 9

Stage 9 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership committed
[✓] Stage 3 Migration discipline committed
[✓] Stage 4 Recommendation read/write split committed
[✓] Stage 5 Metric Truth Layer committed
[✓] Stage 6 Parser facts confidence committed
[✓] Stage 7 Steam cursor truth committed
[✓] Stage 8 AI output validator committed
[✓] FULL_PROJECT_AUDIT_AFTER_STAGE_8.md created
[✓] git push completed
[✓] git status clean
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -12
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой — Stage 9 не начинать.

---

# 2. Главная цель Stage 9

Сделать Coach-first UI поверх уже существующих данных и сервисов.

Stage 9 должен ответить пользователю на первом экране:

```text
1. Что сейчас тренировать?
2. Почему именно это?
3. Насколько данным можно верить?
4. Что делать в следующих матчах?
5. Как понять, что я выполнил рекомендацию?
6. Какой прогресс по текущей рекомендации?
```

Это presentation/usability stage, а не engine stage.

---

# 3. Жёсткие ограничения Stage 9

Запрещено:

```text
- менять DB schema;
- добавлять таблицы/колонки/индексы/constraints;
- делать migrations;
- запускать live Steam calls;
- запускать production Steam/import/parser jobs;
- запускать live AI provider calls;
- делать recommendation planner;
- делать ProblemSnapshot;
- делать parser hardening;
- делать Steam cursor hardening;
- делать AI provider rewrite;
- делать friends/public/multi-user features;
- менять production DB без explicit approval;
- делать commit.
```

Если UI требует planner или новой таблицы, остановиться:

```text
BLOCKED: Stage 9 requires planner/schema change
```

Не выдумывать planner внутри UI.

---

# 4. Разрешённый scope

Разрешено менять:

```text
app/templates/*
app/static/*
app/web/routes.py только read-only/view-model parts
app/services/* только read-only view model helpers, если без side effects
docs/*
tests/*
```

Разрешено:

```text
- rearrange coach page hierarchy;
- add coach-first cards;
- add read-only view model helpers;
- add Metric Truth warnings to UI;
- add AI validation status display;
- add latest-match coach summary using existing data;
- add active/current recommendation block using existing recommendation ordering;
- add empty states;
- add tests for page rendering / no read mutation.
```

Нельзя:

```text
- create new recommendation selection logic pretending to be planner;
- call ensure/evaluate from GET/read path;
- launch background jobs from page render;
- auto-run AI on page load;
- auto-run Steam/import/parser on page load.
```

---

# 5. Stage 9 UI target

## 5.1. Coach page priority

`/coach` should become the main product page.

Top hierarchy:

```text
1. Current tracked recommendation / next action
2. Evidence and confidence
3. Progress / last evaluation
4. Latest match coach summary
5. AI coach report status
6. Secondary stats below
```

## 5.2. Current recommendation card

Use existing active recommendation state.

Must label honestly:

```text
Current tracked recommendation
```

Do not label as:

```text
Verified top problem
```

unless planner/ProblemSnapshot exists.

Card should show:

```text
- title/category
- action
- baseline/current/target if available
- progress status
- next-match instruction
- last evaluation result
- confidence/warnings from Metric Truth if available
```

## 5.3. Evidence/confidence block

Show:

```text
- metric ids/names used as evidence
- metric reliability: trusted/medium/approximate/low/unavailable
- warning labels for approximate/low
- clear text when a metric is not suitable for hard diagnosis
```

Keep copy short. User-facing language, not internal audit prose.

## 5.4. Latest match coach summary

Using existing persisted match/report data only:

```text
- latest match result/date/map if available
- what changed in relation to current recommendation
- whether current recommendation was evaluated
- if not enough data: say so explicitly
```

No new parser job. No live Steam sync.

## 5.5. AI report display

Show AI validation status where AI report exists:

```text
- valid structured report
- fallback/invalid AI output
- warning if old report predates validator if detectable
```

No live AI generation on page load. Buttons must remain explicit.

## 5.6. Dashboard

Do not redesign entire dashboard.

Optional safe change:

```text
- add a compact "Coach next action" preview linking to /coach
```

Do not turn Stage 9 into full dashboard redesign.

---

# 6. Tiny repair allowed

The audit recommended one docs-only repair:

```text
Update docs/KNOWN_LIMITATIONS.md so it no longer contradicts Stage 5 Metric Truth and Stage 8 AI Validator.
```

Allowed in Stage 9 if kept docs-only and small.

---

# 7. Tests

Add/update:

```text
tests/test_coach_first_ui.py
```

Minimum tests:

```text
[ ] /coach renders for authenticated owner
[ ] /coach displays current tracked recommendation when present
[ ] /coach empty state is safe when no recommendation/matches
[ ] /coach surfaces Metric Truth warning labels for approximate/low metrics
[ ] /coach surfaces AI validation/fallback status when report exists
[ ] GET /coach does not mutate recommendation/evaluation row counts
[ ] no live AI/Steam/parser calls are made in page render
[ ] existing full suite passes
```

If templates are hard to assert deeply, test key text markers / response status / DB row counts.

---

# 8. Docs update

Update:

```text
docs/CURRENT_MILESTONE.md
docs/CURRENT_STATUS.md
docs/PROJECT_CONTROL.md
docs/ROADMAP.md
docs/TESTING.md
docs/CHANGELOG.md
docs/KNOWN_LIMITATIONS.md
```

Create:

```text
docs/audit/STAGE_9_COACH_FIRST_UI_IMPLEMENTATION_REPORT.md
docs/audit/COACH_UI_SURFACE_INVENTORY.md
```

---

# 9. Safe checks

Run:

```bash
APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Forbidden:

```text
live AI provider calls
live Steam calls
production Steam/import/parser jobs
production DB mutation
production demo parsing
```

---

# 10. Stage 9 DoD

Stage 9 is implemented only if:

```text
[ ] /coach is coach-first, not stats-first
[ ] current tracked recommendation visible
[ ] evidence/confidence/warnings visible
[ ] next-match action visible
[ ] progress/last evaluation visible if available
[ ] latest match coach summary visible if available
[ ] AI validation/fallback status visible where relevant
[ ] empty states are honest
[ ] GET/read page rendering does not mutate DB
[ ] no schema changes
[ ] no live external jobs/providers
[ ] full pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] production DB SHA unchanged
[ ] implementation report created
```

---

# 11. Implementation prompt for Codex

```text
Начни Stage 9: Coach-first UI.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/ROADMAP.md
- docs/ARCHITECTURE.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/AI_COACH.md
- docs/TESTING.md
- docs/MIGRATIONS.md
- docs/audit/FULL_PROJECT_AUDIT_AFTER_STAGE_8.md
- docs/audit/STAGE_4_RECOMMENDATION_RW_REVIEW.md
- docs/audit/STAGE_5_METRIC_TRUTH_REVIEW.md
- docs/audit/STAGE_8_AI_VALIDATOR_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md

Stage 0–8 завершены и закоммичены.
Full audit after Stage 8: PASS_WITH_WARNINGS.
Git push выполнен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -12
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 9:
сделать Coach-first UI поверх существующих persisted state/services.

Жёсткие ограничения:
- не менять DB schema;
- не добавлять tables/columns/indexes/constraints;
- не делать migrations;
- не запускать live Steam/import/parser jobs;
- не запускать live AI calls;
- не делать recommendation planner;
- не делать ProblemSnapshot;
- не делать parser/Steam/AI engine work;
- не делать friends/public features;
- не менять production DB;
- не делать commit.

Нужно:
1. провести inventory coach UI surfaces;
2. создать docs/audit/COACH_UI_SURFACE_INVENTORY.md;
3. сделать /coach более coach-first:
   - current tracked recommendation;
   - evidence/confidence;
   - Metric Truth warnings;
   - next-match action;
   - progress/last evaluation;
   - latest match coach summary if available;
   - AI validation/fallback status if report exists;
4. сохранить честную формулировку: current tracked recommendation, not verified top problem;
5. добавить safe empty states;
6. optionally add compact dashboard link/preview to /coach, без полного redesign;
7. обновить docs/KNOWN_LIMITATIONS.md, чтобы не противоречил Stage 5/8;
8. добавить tests/test_coach_first_ui.py;
9. обновить docs/CURRENT_MILESTONE.md, docs/CURRENT_STATUS.md, docs/PROJECT_CONTROL.md, docs/ROADMAP.md, docs/TESTING.md, docs/CHANGELOG.md;
10. создать docs/audit/STAGE_9_COACH_FIRST_UI_IMPLEMENTATION_REPORT.md.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
- APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- UI approach chosen
- files changed
- tests added
- safe checks results
- production DB touched: yes/no
- DB SHA before/after
- live AI/Steam/parser/import jobs run: yes/no
- schema changes: yes/no
- remaining risks
- can proceed to Stage 9 review-only: yes/no

Если Stage 9 требует planner/schema/live jobs — остановись и напиши BLOCKED.
```

---

# 12. Review-only prompt

```text
Проведи review-only проверку Stage 9 Coach-first UI.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_9_COACH_FIRST_UI_REVIEW.md

Не запускай live AI calls.
Не запускай live Steam calls.
Не запускай production import/parser jobs.
Не делай commit.
Не переходи к Stage 10.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/AI_COACH.md
- docs/TESTING.md
- docs/audit/FULL_PROJECT_AUDIT_AFTER_STAGE_8.md
- docs/audit/COACH_UI_SURFACE_INVENTORY.md
- docs/audit/STAGE_9_COACH_FIRST_UI_IMPLEMENTATION_REPORT.md
- docs/tasks/STABILIZATION_STAGE_9_COACH_FIRST_UI_TZ_CS2_AI_COACH.md
- current git diff including untracked files

Проверь:
1. /coach is coach-first, not stats-first;
2. current tracked recommendation is visible;
3. UI does not claim verified top problem;
4. evidence/confidence/warnings are visible;
5. Metric Truth approximate/low/unavailable warnings are surfaced;
6. next-match action is visible;
7. progress/last evaluation visible if available;
8. latest match coach summary visible if available;
9. AI validation/fallback status visible where relevant;
10. empty states are safe/honest;
11. GET /coach does not mutate recommendation/evaluation rows;
12. no schema changes;
13. no live AI/Steam/import/parser jobs;
14. no recommendation planner;
15. no ProblemSnapshot;
16. no parser/Steam/AI engine scope creep;
17. tests pass;
18. ruff passes;
19. git diff --check passes;
20. production DB SHA unchanged.

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q
- APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_9_COACH_FIRST_UI_REVIEW.md:

# Stage 9 Coach-first UI Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## UI Truth Review
- Does UI overclaim?
- Does it call current tracked recommendation correctly?
- Are weak metrics labeled?

## Read/Write Safety Review
- Does GET/page render mutate DB?
- Any hidden background jobs?

## Scope Creep Review
- Schema changes?
- Planner?
- ProblemSnapshot?
- Live AI/Steam/parser/import?
- UI redesign outside coach loop?

## Changed Files Reviewed

## Test Results

## Production DB Check

## Remaining Risks

## Must Fix Before Stage 10

## Can Proceed To Stage 10
yes/no
```

---

# 13. Commit after review

If review is PASS/PASS_WITH_WARNINGS without blockers:

```bash
git status --short
git --no-pager diff --stat
git add app docs tests
git commit -m "Make coach UI action-first"
git push
```

---

# 14. After Stage 9

After Stage 9, do not automatically continue to engine work.

Run a small decision gate:

```text
A. If UI is usable enough for personal MVP:
   Stage 10 = Personal MVP runtime smoke / release gate.

B. If UI exposes that defaults are not enough:
   Stage 10 = ProblemSnapshot + Recommendation Planner, with explicit migration planning.

C. If Steam reliability blocks usage:
   Stage 10 = Steam worker/retry ledger, with explicit migration planning.
```

