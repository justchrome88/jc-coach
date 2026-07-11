# CS2 AI Coach — Stabilization Stage 8 / AI Output Validator TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 8 после закрытия Stage 7 Steam cursor truth.  
Фокус: сделать AI coach output проверяемым, ограниченным схемой и не позволяющим AI уверенно врать поверх слабых метрик.

---

# 1. Статус перед Stage 8

Stage 8 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership / enforced single-owner boundaries committed
[✓] Stage 3 Migration discipline committed
[✓] Stage 4 Recommendation read/write split committed
[✓] Stage 5 Metric Truth Layer committed
[✓] Stage 6 Parser facts & confidence hardening committed
[✓] Stage 7 Steam cursor truth committed
[✓] git push completed
[✓] git status clean
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -11
sha256sum data/cs2_coach.db
```

Если `git status --short` не пустой — Stage 8 не начинать.

---

# 2. Главная проблема Stage 8

После Stage 5–7 система стала честнее по метрикам, parser facts и Steam cursor. Но AI layer всё ещё может быть слабым местом:

```text
- AI output free-form Markdown;
- нет строгой проверки структуры ответа;
- нет validator, который запрещает unsupported claims;
- AI может сделать confident diagnosis на suppressed/approximate metric;
- AI может выдать рекомендации, не связанные с metric truth / evidence;
- AI может игнорировать ограничения parser confidence;
- AI failure/invalid output behavior может быть недетерминированным.
```

Это опасно: если AI красиво сформулирует ложный диагноз, пользователь поверит именно AI, а не audit docs.

---

# 3. Главная цель Stage 8

Ввести AI Output Validator без schema changes и без live AI provider calls.

После Stage 8:

```text
1. AI coach output имеет ожидаемую структуру;
2. output проходит validation before persisted/displayed where applicable;
3. suppressed/unavailable metrics cannot become hard claims;
4. approximate/warn metrics require caveat/warning;
5. invalid AI output gets safe fallback/error behavior;
6. tests use mocked AI responses only;
7. no live provider calls;
8. no production DB mutation.
```

Stage 8 не обязан делать идеальный AI coach. Он обязан поставить guardrails.

---

# 4. Жёсткие ограничения Stage 8

Запрещено:

```text
- менять DB schema;
- добавлять таблицы/колонки/индексы/constraints;
- делать migrations;
- запускать live AI provider calls;
- запускать production Steam/import/parser jobs;
- делать parser hardening;
- делать Steam cursor work;
- делать recommendation planner;
- делать ProblemSnapshot;
- делать UI redesign;
- делать SaaS/friends/billing;
- менять production DB без explicit approval;
- делать commit.
```

Если Codex считает, что Stage 8 невозможно сделать без schema changes для хранения structured AI output — он должен остановиться:

```text
BLOCKED: Stage 8 requires schema change for structured AI output persistence
```

---

# 5. Preferred approach

Stage 8 должен быть validator/service layer, не DB layer.

Допустимая реализация:

```text
app/services/ai_validator.py
app/services/ai_coach.py minimal integration
tests/test_ai_validator.py
```

Допустимая структура output schema:

```text
CoachOutput:
- summary
- diagnoses[]
- recommendations[]
- warnings[]
- evidence[]
- confidence
```

Допустимая структура diagnosis:

```text
Diagnosis:
- category
- severity
- claim
- evidence_metric_ids[]
- evidence_values optional
- confidence
- caveats[]
```

Допустимая структура recommendation:

```text
Recommendation:
- category
- action
- rationale
- target_metric_ids[]
- measurable_goal optional
- confidence
- caveats[]
```

Имена могут быть другими. Важен смысл: AI output должен быть валидируемым, а не просто красивым Markdown.

Если текущий AI output хранится/displayed как Markdown, Stage 8 может:

```text
- валидировать intermediate structured payload;
- затем render to Markdown;
- или validate extracted/declared structure before accepting;
- или provide safe fallback if provider output invalid.
```

Без schema changes.

---

# 6. Scope Stage 8

## 6.1. Inventory AI output surfaces

Найти AI-related code:

```bash
rg -n "ai|coach|provider|OpenAI|markdown|prompt|completion|response|recommendation|diagnosis|metric_truth|confidence|schema|validator" app tests docs
```

Создать:

```text
docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md
```

Inventory должен зафиксировать:

```text
- где формируется AI prompt;
- где вызывается provider;
- где AI response парсится/сохраняется/показывается;
- какие metric_truth данные уже передаются;
- где нет validation;
- какие unsupported claim risks остаются.
```

## 6.2. Define validation policy

Policy должна запрещать:

```text
- hard claim using suppressed metric;
- hard claim using unavailable metric;
- confident recommendation from approximate metric without caveat;
- recommendation without evidence metric or rationale;
- output without required sections;
- hallucinated metric id unknown to Metric Truth registry;
- claims stronger than available reliability.
```

Допустимые decisions:

```text
allowed
warn
reject
fallback
```

## 6.3. Validator implementation

Добавить validator, который умеет:

```text
- validate structured AI output;
- validate metric ids against Metric Truth Layer;
- validate usage policy: diagnosis/recommendation/AI;
- return warnings/rejections;
- produce safe fallback output if invalid;
- be unit-testable without DB/provider.
```

Не надо делать heavy framework, если не нужен. Простые dataclass/TypedDict/helpers допустимы.

## 6.4. AI coach integration

Минимально подключить validator:

```text
- provider response should be validated before use where clean integration point exists;
- prompt should instruct structured output only if current flow supports it safely;
- invalid output should not crash page/job;
- invalid output should not be accepted as confident coach advice.
```

Если текущий provider flow слишком free-form для strict schema без большого rewrite:

```text
- implement validator and safe Markdown fallback;
- validate internal AI payload / planned output;
- document remaining free-form limitation as PASS_WITH_WARNINGS;
- do not rewrite whole AI provider stack.
```

## 6.5. Tests

Добавить:

```text
tests/test_ai_validator.py
```

Минимум:

```text
[ ] valid structured output passes
[ ] missing required sections rejected/fallback
[ ] unknown metric id rejected/warned
[ ] suppressed metric cannot support hard diagnosis
[ ] unavailable metric cannot support recommendation
[ ] approximate metric requires caveat/warning
[ ] invalid provider output does not crash and returns safe fallback
[ ] tests use mocked provider/output only
[ ] no live AI calls
[ ] no production DB used
```

Если есть existing AI coach tests — добавить минимальные regression tests.

## 6.6. Docs update

Обновить:

```text
docs/AI_COACH.md
docs/METRICS.md если AI usage policy clarified
docs/RECOMMENDATIONS.md если recommendation output constraints clarified
docs/CURRENT_MILESTONE.md
docs/CURRENT_STATUS.md
docs/PROJECT_CONTROL.md
docs/ROADMAP.md
docs/TESTING.md если добавлен test file
docs/CHANGELOG.md
```

Создать:

```text
docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md
docs/audit/STAGE_8_AI_VALIDATOR_IMPLEMENTATION_REPORT.md
```

---

# 7. Safe checks

Запускать:

```bash
APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q
APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Запрещено запускать:

```text
live AI provider calls
production Steam sync jobs
production import/parser jobs
production demo parsing
production DB mutation
```

---

# 8. Production DB safety

Stage 8 должен сохранить production DB SHA unchanged.

Known hash before Stage 8:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Если SHA меняется без explicit approval — Stage 8 FAIL/BLOCKED.

---

# 9. Stage 8 DoD

Stage 8 считается реализованным только если:

```text
[ ] AI output validation inventory created
[ ] AI output schema/policy documented
[ ] validator implemented
[ ] validator checks Metric Truth usage policy
[ ] suppressed/unavailable metrics cannot become hard claims
[ ] approximate metrics require caveats/warnings
[ ] invalid AI output has safe fallback
[ ] mocked tests added
[ ] no live AI provider calls
[ ] no production Steam/import/parser jobs
[ ] no production DB mutation
[ ] no schema changes
[ ] full pytest passes
[ ] ruff passes
[ ] git diff --check passes
[ ] implementation report created
```

---

# 10. Implementation prompt for Codex

```text
Начни Stage 8: AI output validator.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_8_AI_VALIDATOR_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/AI_COACH.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/TESTING.md
- docs/MIGRATIONS.md
- docs/audit/METRIC_TRUTH_INVENTORY.md
- docs/audit/STAGE_5_METRIC_TRUTH_REVIEW.md
- docs/audit/STAGE_6_PARSER_HARDENING_REVIEW.md
- docs/audit/STAGE_7_STEAM_CURSOR_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_8_AI_VALIDATOR_TZ_CS2_AI_COACH.md

Stage 0 Safety Foundation завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.
Stage 2 Ownership / enforced single-owner boundaries завершён и закоммичен.
Stage 3 Migration discipline завершён и закоммичен.
Stage 4 Recommendation read/write split завершён и закоммичен.
Stage 5 Metric Truth Layer завершён и закоммичен.
Stage 6 Parser facts & confidence hardening завершён и закоммичен.
Stage 7 Steam cursor truth завершён и закоммичен.
Git push выполнен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -11
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 8:
ввести AI Output Validator без schema changes и без live AI calls, чтобы AI coach не мог принимать/показывать confident unsupported claims.

Жёсткие ограничения:
- не менять DB schema;
- не добавлять таблицы/колонки/индексы/constraints;
- не делать migrations;
- не запускать live AI provider calls;
- не запускать production Steam/import/parser jobs;
- не делать parser hardening;
- не делать Steam cursor work;
- не делать recommendation planner;
- не делать ProblemSnapshot;
- не делать UI redesign;
- не менять production DB без explicit approval;
- не делать commit.

Нужно:
1. провести inventory AI output surfaces;
2. создать docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md;
3. определить AI output schema/policy;
4. реализовать validator, который проверяет:
   - required structure;
   - metric ids against Metric Truth Layer;
   - suppressed/unavailable metric usage;
   - approximate metric caveats/warnings;
   - unknown metric ids;
5. добавить safe fallback for invalid output;
6. подключить validator к AI coach only where clean integration point exists;
7. добавить tests/test_ai_validator.py with mocked outputs only;
8. обновить docs/AI_COACH.md, docs/METRICS.md при необходимости, docs/RECOMMENDATIONS.md при необходимости, docs/CURRENT_MILESTONE.md, docs/CURRENT_STATUS.md, docs/PROJECT_CONTROL.md, docs/CHANGELOG.md, docs/TESTING.md;
9. создать docs/audit/STAGE_8_AI_VALIDATOR_IMPLEMENTATION_REPORT.md.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q
- APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- AI validator approach chosen
- files changed
- tests added
- safe checks results
- production DB touched: yes/no
- DB SHA before/after
- live AI calls run: yes/no
- import/Steam/parser jobs run: yes/no
- schema changes: yes/no
- remaining risks
- can proceed to Stage 8 review-only: yes/no

Если считаешь, что для Stage 8 нужны schema changes or live AI calls — остановись и напиши BLOCKED.
```

---

# 11. Review-only prompt for Codex

После implementation обязательно отдельный review-only pass:

```text
Проведи review-only проверку Stage 8 AI output validator.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_8_AI_VALIDATOR_REVIEW.md

Не запускай live AI calls.
Не запускай import/Steam/parser production jobs.
Не делай commit.
Не переходи к Stage 9.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/AI_COACH.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/TESTING.md
- docs/MIGRATIONS.md
- docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md
- docs/audit/STAGE_8_AI_VALIDATOR_IMPLEMENTATION_REPORT.md
- docs/tasks/STABILIZATION_STAGE_8_AI_VALIDATOR_TZ_CS2_AI_COACH.md
- текущий git diff, включая untracked files

Проверь Stage 8 DoD:
1. AI output validation inventory exists and is accurate;
2. AI output schema/policy documented;
3. validator exists;
4. validator checks Metric Truth usage policy;
5. suppressed/unavailable metrics cannot become hard diagnosis/recommendation;
6. approximate metrics require caveats/warnings;
7. unknown metric ids are safe;
8. invalid AI output has safe fallback;
9. tests are mocked and do not perform live AI calls;
10. no production Steam/import/parser jobs run;
11. no production DB mutation;
12. no schema changes;
13. full safe pytest passes;
14. ruff passes;
15. git diff --check passes;
16. no parser hardening;
17. no Steam cursor work;
18. no recommendation planner;
19. no ProblemSnapshot;
20. no UI redesign.

Особо проверь:
- app/services/ai_validator.py
- app/services/ai_coach.py
- app/services/metric_truth.py if changed
- tests/test_ai_validator.py
- docs/AI_COACH.md
- docs/audit/AI_OUTPUT_VALIDATION_INVENTORY.md
- docs/audit/STAGE_8_AI_VALIDATOR_IMPLEMENTATION_REPORT.md

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q
- APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Создай docs/audit/STAGE_8_AI_VALIDATOR_REVIEW.md:

# Stage 8 AI Validator Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## AI Validator Review

Отдельно ответь:
- what schema/policy is enforced;
- what invalid outputs are rejected/fallback;
- how Metric Truth policy is enforced;
- whether unsupported confident claims can still pass.

## Live AI / Job Safety Review

Отдельно ответь:
- were any live AI calls made;
- were any production Steam/import/parser jobs run;
- do tests use only mocked outputs/providers.

## Integration Review

Отдельно ответь:
- what changed in ai_coach;
- is this minimal validator integration or provider rewrite;
- does invalid output fail safe.

## Schema Change Review

Отдельно ответь:
- были ли schema changes;
- если нет, подтвердить;
- если да, Stage 8 FAIL unless explicit approved migration path exists.

## Scope Creep Review

Отдельно ответь:
- был ли parser hardening;
- был ли Steam cursor work;
- был ли recommendation planner;
- был ли ProblemSnapshot;
- был ли UI redesign.

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 9

## Can Proceed To Stage 9
yes/no

Если Stage 8 не проходит — не исправляй, только напиши, что именно не проходит.
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
git commit -m "Add AI output validator"
```

После commit:

```bash
git status --short
git log --oneline -11
```

---

# 13. Next stage

После Stage 8:

```text
Stage 9: Coach-first UI
```

Stage 9 не начинать без:

```text
Stage 8 implementation → review-only → repair if needed → commit
```

