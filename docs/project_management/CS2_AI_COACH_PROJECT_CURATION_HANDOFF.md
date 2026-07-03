# CS2 AI Coach — Project Curation Handoff / Operating Manual

Дата: 2026-07-03  
Назначение: резервная инструкция для продолжения проекта, если текущий чат потеряет контекст, начнёт лагать или нужно будет передать управление новому чату/модели.

---

# 1. Главный принцип

Проект больше нельзя вести как “Codex что-то делает, потом посмотрим”.

Проект ведётся как controlled hardening pipeline:

```text
Stage task → Codex implementation → safe checks → review-only pass → repair if needed → commit → next stage
```

Каждый stage должен быть маленьким, проверяемым и закоммиченным отдельно.

Запрещено перескакивать stages, даже если Codex пишет “можно продолжать”.

---

# 2. Текущий статус проекта

Фактический уровень продукта:

```text
v0.4-alpha foundation
```

Текущий milestone разработки:

```text
v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop
```

Уже сделано:

```text
[✓] Documentation chaos cleanup
[✓] Source of truth docs
[✓] Instructions validation
[✓] Full read-only project audit
[✓] Stage 0: Safety Foundation
[✓] Stage 1: Security P0
```

Следующий этап:

```text
[→] Stage 2: Ownership / enforced single-user boundaries
```

Дальше по плану:

```text
[ ] Stage 3: Migration discipline
[ ] Stage 4: Recommendation read/write split
[ ] Stage 5: Metric Truth Layer
[ ] Stage 6: Parser hardening
[ ] Stage 7: Steam cursor truth
[ ] Stage 8: AI validator
[ ] Stage 9: Coach-first UI
[ ] Stage 10: Friends alpha gate
```

---

# 3. Ключевые факты, которые нельзя забыть

## 3.1. После Stage 0

Stage 0 закрыл Safety Foundation:

- backup/restore;
- test isolation;
- safe pytest на temp DB;
- production DB SHA до/после не менялся;
- `pytest`, `ruff`, `git diff --check` зелёные;
- импорт, Steam jobs и parser jobs не запускались.

Stage 0 commit:

```text
7c0b777 Add safety foundation with backup and isolated tests
```

## 3.2. После Stage 1

Stage 1 закрыл Security P0:

- non-health `/api/*` больше не public;
- `/health` остался public;
- session/API auth добавлены;
- CSRF для web POST и session-authenticated API state changes;
- Bearer `API_TOKEN` path покрыт тестами;
- MVP process-local rate limits;
- strong session secret fail-fast;
- Steam OpenID callback проверяет `check_authentication`;
- dangerous jobs protected;
- safe pytest: 90 passed;
- ruff passed;
- git diff --check passed;
- production DB SHA unchanged;
- import/Steam/parser production jobs не запускались.

Stage 1 был закоммичен пользователем после repair-pass.

Если новый чат продолжает проект, первым делом нужно проверить:

```bash
git log --oneline -5
git status --short
```

Ожидаемо должен быть commit типа:

```text
Add Security P0 hardening
```

и чистый или объяснимый `git status`.

---

# 4. Source of truth documents

Новый чат/agent всегда сначала читает:

```text
AGENT.md
docs/PROJECT_CONTROL.md
docs/CURRENT_STATUS.md
docs/CURRENT_MILESTONE.md
docs/VERSION_MAP.md
docs/ROADMAP.md
docs/SECURITY.md
docs/TESTING.md
docs/BACKUP_RESTORE.md
docs/RELEASE_CHECKLIST.md
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
```

Старые `instructions/*`, roadmap scoring, competitor matrix, old prompts — historical/supporting only. Они не являются текущим планом.

---

# 5. Общий gate для каждого stage

Stage считается закрытым только если есть:

```text
[ ] stage implementation завершён
[ ] safe tests passed
[ ] ruff passed
[ ] git diff --check passed
[ ] production DB SHA unchanged или изменение явно разрешено stage-ом
[ ] import/Steam/parser jobs не запускались, если stage это запрещает
[ ] review-only pass создан
[ ] review result PASS или PASS_WITH_WARNINGS без blockers
[ ] repair-pass сделан, если review нашёл blockers
[ ] docs обновлены
[ ] git diff просмотрен
[ ] commit сделан
[ ] git status clean
```

Если нет commit — stage не закрыт.

---

# 6. Обязательные команды проверки

Перед stage:

```bash
cd /opt/jc-coach
git status --short
git --no-pager diff --stat
git log --oneline -5
sha256sum data/cs2_coach.db
```

После implementation/review:

```bash
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
git status --short
git --no-pager diff --stat
```

Для просмотра изменений:

```bash
git --no-pager diff --name-only
git --no-pager diff --stat
git --no-pager diff -- app/main.py
```

Не использовать обычный `git diff`, если терминал зависает в pager. Использовать `git --no-pager diff`.

---

# 7. Что делать, если текущий чат потерян

В новом чате написать:

```text
Ты куратор проекта CS2 AI Coach. Продолжи controlled hardening pipeline.

Прочитай этот handoff-файл и ориентируйся на него как на краткое состояние проекта.

Текущее состояние:
- docs chaos cleanup done;
- full read-only audit done;
- Stage 0 Safety Foundation done and committed;
- Stage 1 Security P0 done and committed;
- следующий этап: Stage 2 Ownership / enforced single-user boundaries.

Стиль:
- отвечай по-русски;
- жёстко контролируй scope;
- не разрешай feature creep;
- каждый stage: implementation → review-only → repair → commit;
- не переходи к следующему stage без commit.

Сначала дай план Stage 2 и prompt для Codex.
```

К новому чату желательно приложить:

```text
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
этот handoff-файл
```

И прислать вывод:

```bash
git log --oneline -5
git status --short
```

---

# 8. Роль ChatGPT-куратора

ChatGPT-куратор не должен писать “продолжай” вслепую.

Его задачи:

1. Держать общий stage plan.
2. Проверять отчёты Codex.
3. Говорить, можно ли закрывать stage.
4. Говорить, что коммитить.
5. Запрещать feature creep.
6. Подготавливать следующий stage task.
7. Требовать review-only pass.
8. Проверять, что production DB не тронута.
9. Проверять, что тесты safe.
10. Останавливать процесс, если Codex пытается смешать stages.

Куратор не должен заменять CI, backup и tests. Он принимает решения по процессу, но доказательства должны быть в repo: tests, docs, review reports, commits.

---

# 9. Роль Codex

Codex должен работать только stage-by-stage.

Для каждого stage:

```text
1. Прочитать AGENT.md и PROJECT_CONTROL.
2. Прочитать текущий stage task.
3. Показать git status и diff stat.
4. Дать план файлов.
5. Реализовать только текущий stage.
6. Запустить safe checks.
7. Создать/обновить stage report.
8. Остановиться.
```

Codex не должен:

- переходить к следующему stage сам;
- делать commit без явной просьбы пользователя;
- запускать production import/Steam/parser jobs;
- менять production DB без backup и явного разрешения;
- добавлять новые фичи;
- трогать viewer/heatmaps/clips/FACEIT/friends/public/social/payments до соответствующего gate.

---

# 10. Stage 2 — следующий этап

Название:

```text
Stage 2: Ownership / enforced single-user boundaries
```

Главная продуктовая правда:

Сейчас проект не готов к multi-user/friends, потому что core data ownership ещё не гарантирован. Но сразу делать полноценный multi-user слой рискованно. Правильный следующий шаг — enforced single-owner mode.

## 10.1. Цель Stage 2

Сделать так, чтобы приложение явно работало как single-owner instance:

```text
один owner user владеет всеми локальными match/report/recommendation/Steam/job данными,
а public/register/OpenID/API paths не могут создать неконтролируемое чужое состояние.
```

## 10.2. Не цель Stage 2

Не делать:

- полноценный multi-user SaaS;
- friends/social/public profiles;
- payments;
- Metric Truth Layer;
- parser hardening;
- recommendation planner;
- AI validator;
- UI redesign;
- migrations, кроме минимально необходимых и safe после backup;
- FACEIT;
- viewer/heatmaps/clips.

## 10.3. Stage 2 задачи

```text
[ ] определить owner user policy
[ ] запретить или ограничить регистрацию новых пользователей
[ ] сделать настройки instance ownership
[ ] проверить Steam OpenID callback: он не должен создавать/линковать чужие данные вне owner boundary
[ ] гарантировать, что current_user boundaries согласованы
[ ] закрыть сценарий: второй пользователь регистрируется и видит/мутирует данные
[ ] закрыть сценарий: public callback создаёт запись для не-owner user
[ ] добавить tests на owner boundary
[ ] обновить docs/SECURITY.md
[ ] обновить docs/CURRENT_MILESTONE.md
[ ] обновить docs/RELEASE_CHECKLIST.md
[ ] создать review report
```

## 10.4. Важное архитектурное решение

Предпочтительный вариант сейчас:

```text
enforced single-user mode
```

а не полноценный multi-user ownership.

Причина:

- проект личный;
- core tables без `user_id`;
- полноценный ownership потребует крупных schema changes;
- migration discipline ещё не закрыт;
- перед friends alpha достаточно single-owner instance boundary;
- multi-user можно делать позже отдельным stage после migrations.

---

# 11. Stage 2 suggested task prompt

```text
Начни Stage 2: Ownership / enforced single-user boundaries.

Перед работой прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_MILESTONE.md
- docs/SECURITY.md
- docs/TESTING.md
- docs/BACKUP_RESTORE.md
- docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
- docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
- docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
- docs/audit/API_SECURITY_INVENTORY.md

Stage 0 завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.

Цель Stage 2:
реализовать enforced single-user / single-owner boundaries, не полноценный multi-user SaaS.

Нужно:
1. Сначала показать:
   - git status --short
   - git diff --stat
   - git log --oneline -5
   - краткий план изменений по файлам

2. Реализовать только Stage 2:
   - определить owner user policy;
   - запретить/ограничить регистрацию новых пользователей согласно owner policy;
   - закрыть риск, что `/auth/steam/callback` создаёт/линкует чужие данные вне owner boundary;
   - добавить проверки owner boundary для web/API/current_user;
   - добавить tests на второй user / registration / Steam callback / API access;
   - обновить docs/SECURITY.md, docs/CURRENT_MILESTONE.md, docs/RELEASE_CHECKLIST.md;
   - создать docs/audit/STAGE_2_OWNERSHIP_REVIEW.md или отдельный implementation report.

Жёсткие ограничения:
- не делать полноценный multi-user ownership через массовое добавление user_id во все core tables;
- не делать migrations без отдельного backup/restore and explicit plan;
- не делать Metric Truth Layer;
- не делать parser hardening;
- не делать recommendation planner;
- не делать AI validator;
- не делать UI redesign;
- не запускать import/Steam/parser production jobs;
- не менять production DB без отдельного backup;
- не делать commit.

Проверки:
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
- can proceed to Stage 3 yes/no
```

---

# 12. Stage 2 review-only prompt

После Stage 2 implementation обязательно запустить review-only:

```text
Проведи review-only проверку Stage 2 Ownership / enforced single-user boundaries.

Ничего не меняй в коде, тестах и документации, кроме создания review-отчёта:
docs/audit/STAGE_2_OWNERSHIP_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к Stage 3.

Проверь:
1. owner policy clearly documented;
2. registration policy enforced;
3. second user cannot create uncontrolled state;
4. second user cannot access/mutate owner data;
5. Steam OpenID callback cannot link/create data outside owner boundary;
6. API auth from Stage 1 still works;
7. CSRF/rate limits from Stage 1 still work;
8. production DB SHA unchanged unless explicitly allowed;
9. safe pytest passed;
10. ruff passed;
11. git diff --check passed.

Запусти:
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db

Отчёт:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- Evidence by DoD item
- Changed files reviewed
- Remaining risks
- Must fix before Stage 3
- Can proceed to Stage 3: yes/no
```

---

# 13. Как коммитить stages

После successful review:

```bash
git status --short
git --no-pager diff --stat
```

Если нет `data/*.db`, `.env`, runtime artifacts:

```bash
git add app docs tests .env.example scripts
git commit -m "Add <stage name>"
```

Например:

```bash
git commit -m "Add enforced single-owner boundaries"
```

После commit:

```bash
git status --short
git log --oneline -5
```

---

# 14. Что делать при FAIL/BLOCKED

Не переходить дальше.

Дать Codex repair-only prompt:

```text
Исправь только FAIL/BLOCKED пункты из docs/audit/<STAGE_REVIEW>.md.
Не переходи к следующему stage.
Не добавляй новые фичи.
Не трогай запрещённые области.
После исправления снова запусти safe checks и обнови review report.
```

---

# 15. Когда можно ускоряться

Можно делать несколько stages за вечер только при строгом цикле:

```text
stage implementation → review-only → repair → commit → next stage
```

Нельзя:

```text
Stage 2 → Stage 3 → Stage 4 одним большим промптом
```

Пока automated gates недостаточно сильные, это вернёт проект в хаос.

---

# 16. Главная антиошибка

Не принимать “Codex сказал, что всё готово” как доказательство.

Доказательство — это:

- diff;
- tests;
- review report;
- DB hash;
- no jobs;
- clean commit.

---

# 17. Краткий план на ближайшее время

1. Убедиться, что Stage 1 commit сделан.
2. Проверить `git status --short`.
3. Запустить Stage 2 implementation prompt.
4. Получить Stage 2 report.
5. Запустить Stage 2 review-only prompt.
6. Если PASS/PASS_WITH_WARNINGS без blockers — commit.
7. Только потом Stage 3 Migration discipline.

---

# 18. Текущая позиция для нового чата

Если этот файл открывается в новом чате, считать текущей задачей:

```text
Подготовить и провести Stage 2: Ownership / enforced single-user boundaries.
```

Не возвращаться к обсуждению идеи проекта, конкурентов, UI, AI coach, метрик или parser до закрытия Stage 2.

