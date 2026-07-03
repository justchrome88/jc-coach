# ТЗ для Codex CLI: аудит и консолидация инструкций проекта CS2 AI Coach

Дата: 2026-07-02  
Назначение: привести накопившиеся инструкции, roadmap-файлы, ТЗ, docs и agent-rules к единой системе управления проектом.  
Главный принцип: сначала аудит и карта конфликтов, потом аккуратная консолидация. Не переписывать проект хаотично.

---

# 1. Зачем это нужно

В проекте накопилось много инструкций: README, `docs/`, `instructions/`, audit-файлы, roadmap-файлы, планы по метрикам, security, Steam, AI coach, recommendation tracking и т.д.

Это уже опасно.

Если у проекта много инструкций без иерархии, Codex начинает работать плохо не потому, что он “не понимает”, а потому что получает противоречивые или устаревшие сигналы:

- один файл говорит “MVP v0.1”;
- другой файл описывает уже v0.4/v0.6;
- один roadmap говорит “делаем Steam”;
- другой говорит “заморозить Steam до security”;
- один документ описывает метрики как готовые;
- аудит говорит, что часть метрик best-effort;
- один файл толкает в новые фичи;
- другой требует hardening;
- часть инструкций является исторической, но выглядит как актуальная.

Цель этого ТЗ — сделать из хаоса управляемую документационную систему.

---

# 2. Главная команда Codex

Твоя задача: провести аудит всех инструкций и документации проекта, найти дубли/конфликты/устаревшие документы и создать единый комплект актуальной документации.

Не надо менять бизнес-логику проекта, backend, frontend, database или метрики. Это задача про документацию, управление проектом и инструкции для будущей работы.

---

# 3. Жёсткие ограничения

## 3.1. Запрещено

1. Менять код приложения.
2. Менять модели БД.
3. Делать миграции.
4. Запускать парсеры/импорты/Steam jobs.
5. Удалять старые документы.
6. Массово переписывать README без audit-карты.
7. Делать git commit до завершения audit phase.
8. Считать старые документы ложными без доказательств.
9. Прятать конфликты.
10. Подменять реальность красивым roadmap.

## 3.2. Разрешено

1. Читать файлы.
2. Создавать новые docs-файлы.
3. Перемещать старые инструкции в архив только после создания карты.
4. Добавлять в старые файлы шапку `DEPRECATED` / `HISTORICAL` / `SUPERSEDED`, если принято решение.
5. Создать `docs/archive/`, если её нет.
6. Создать один главный индекс документации.
7. Создать правила для будущей работы Codex.
8. Делать commit только после завершения этапа и проверки git diff.

---

# 4. Главная цель консолидации

После работы должен появиться единый источник правды:

```text
docs/PROJECT_CONTROL.md
```

Он должен отвечать:

1. Что это за проект?
2. Какая текущая фактическая версия?
3. Какой текущий milestone?
4. Какие документы актуальны?
5. Какие документы исторические?
6. Что Codex должен читать перед работой?
7. Какие фичи сейчас запрещены?
8. Как добавлять новые задачи?
9. Как закрывать milestones?
10. Как не расползаться в scope creep?

---

# 5. Целевая структура документации

Нужно привести документацию к такой системе:

```text
README.md
AGENT.md
LATER.md

docs/
  PROJECT_CONTROL.md
  CURRENT_STATUS.md
  VERSION_MAP.md
  CURRENT_MILESTONE.md
  ROADMAP.md
  ARCHITECTURE.md
  METRICS.md
  RECOMMENDATIONS.md
  SECURITY.md
  STEAM_IMPORT.md
  AI_COACH.md
  TESTING.md
  DEPLOYMENT.md
  BACKUP_RESTORE.md
  DECISIONS.md
  CHANGELOG.md
  KNOWN_LIMITATIONS.md
  RELEASE_CHECKLIST.md

docs/audit/
  INSTRUCTIONS_AUDIT_REPORT.md
  INSTRUCTIONS_INVENTORY.md
  DOCUMENT_CONFLICTS.md
  DOCUMENT_DEPRECATION_PLAN.md

docs/archive/
  historical files if needed
```

Если уже существуют похожие файлы, не плодить дубликаты без необходимости. Лучше обновить/объединить.

---

# 6. Иерархия документов

После консолидации должна быть такая иерархия:

## Level 0 — Entry points

### `README.md`
Короткое описание проекта и как запустить.

### `AGENT.md`
Правила для Codex/AI-агентов: что читать, что можно менять, что запрещено, текущий процесс.

### `docs/PROJECT_CONTROL.md`
Главный центр управления проектом.

## Level 1 — Current truth

### `docs/CURRENT_STATUS.md`
Фактическое состояние проекта сейчас.

### `docs/CURRENT_MILESTONE.md`
Что делается прямо сейчас.

### `docs/VERSION_MAP.md`
Какие версии закрыты/частично закрыты/не готовы.

### `docs/ROADMAP.md`
Порядок развития.

## Level 2 — Domain specs

### `docs/ARCHITECTURE.md`
Архитектура.

### `docs/METRICS.md`
Формулы, reliability, suppression rules.

### `docs/RECOMMENDATIONS.md`
Diagnosis -> recommendation -> evaluation -> progress.

### `docs/SECURITY.md`
Auth, API, CSRF, user ownership, friends/public readiness.

### `docs/STEAM_IMPORT.md`
Steam OpenID, Game Authentication Code, knowncode cursor, demo URL, cursor freshness.

### `docs/AI_COACH.md`
AI payload, prompt, structured output, validation, fallback.

## Level 3 — Operations

### `docs/TESTING.md`
Как запускать тесты безопасно.

### `docs/DEPLOYMENT.md`
Как деплоить.

### `docs/BACKUP_RESTORE.md`
Как бэкапить и восстанавливать БД.

### `docs/RELEASE_CHECKLIST.md`
Чеклист перед personal/friends/public релизом.

## Level 4 — History

### `docs/DECISIONS.md`
Почему были приняты решения.

### `docs/CHANGELOG.md`
Что менялось.

### `docs/archive/`
Исторические документы.

---

# 7. Phase 0 — Read-only inventory

Начать с безопасного осмотра.

Выполнить:

```bash
pwd
git status --short
git branch --show-current || true
git log --oneline -10 || true
find . -maxdepth 3 -type f \( -name "*.md" -o -name "*.txt" \) | sort
find instructions docs -maxdepth 3 -type f 2>/dev/null | sort
```

Прочитать:

```bash
cat README.md 2>/dev/null || true
cat AGENT.md 2>/dev/null || true
cat instructions/00_PROJECT_BRIEF.md 2>/dev/null || true
```

Не менять файлы на этом этапе.

---

# 8. Phase 1 — Instructions inventory

Создать:

```text
docs/audit/INSTRUCTIONS_INVENTORY.md
```

Для каждого найденного `.md/.txt` документа указать:

```markdown
| File | Type | Current/Historical/Unknown | Main topic | Still relevant? | Conflicts? | Action |
|---|---|---|---|---|---|---|
```

Типы:

```text
project_brief
roadmap
feature_spec
metric_spec
security_spec
audit_report
task_plan
codex_instruction
historical_worklog
deployment_doc
testing_doc
steam_doc
ai_doc
unknown
```

Статусы:

```text
current
partially_current
historical
superseded
conflicting
unknown
```

Action:

```text
keep
merge
summarize
archive
mark_deprecated
replace
needs_review
```

---

# 9. Phase 2 — Conflict audit

Создать:

```text
docs/audit/DOCUMENT_CONFLICTS.md
```

Найти конфликты по темам:

## 9.1. Product version conflicts

Примеры:

- один файл говорит `v0.1`;
- другой показывает `v0.4-alpha`;
- roadmap опережает реальность.

## 9.2. Scope conflicts

Примеры:

- один файл предлагает Steam/FACEIT/viewer;
- другой требует freeze до security/hardening.

## 9.3. Security conflicts

Примеры:

- где-то написано “можно друзьям”;
- аудит говорит API public / no user ownership.

## 9.4. Metrics conflicts

Примеры:

- метрика показана как готовая;
- аудит говорит best-effort/unreliable.

## 9.5. Recommendation conflicts

Примеры:

- fixed categories vs top verified problem.

## 9.6. Steam import conflicts

Примеры:

- OpenID perceived as enough;
- реальность: нужен Game Authentication Code + knowncode cursor;
- knowncode=0 returns HTTP 412;
- stale cursor problem.

## 9.7. AI coach conflicts

Примеры:

- AI described as coach;
- фактически AI output free-form markdown without validator.

Для каждого конфликта:

```markdown
## Conflict: short title

### Files involved
- ...

### What conflicts
...

### Current truth
...

### Decision
...

### Required documentation update
...
```

---

# 10. Phase 3 — Source-of-truth map

Создать:

```text
docs/PROJECT_CONTROL.md
```

Этот файл должен быть главным входом.

Структура:

```markdown
# Project Control — CS2 AI Coach

## 1. Project Goal

Персональный CS2 AI-тренер, который работает по циклу:
Match -> Facts -> Metrics -> Diagnosis -> Primary Recommendation -> Evaluation -> Progress -> AI Explanation.

## 2. Current Truth

Фактическая версия:
...

## 3. Current Milestone

...

## 4. Source-of-truth Documents

| Topic | Canonical document | Notes |
|---|---|---|
| Product status | docs/CURRENT_STATUS.md | ... |
| Roadmap | docs/ROADMAP.md | ... |
| Architecture | docs/ARCHITECTURE.md | ... |
| Metrics | docs/METRICS.md | ... |
| Recommendations | docs/RECOMMENDATIONS.md | ... |
| Security | docs/SECURITY.md | ... |
| Steam import | docs/STEAM_IMPORT.md | ... |
| AI coach | docs/AI_COACH.md | ... |
| Testing | docs/TESTING.md | ... |
| Deployment | docs/DEPLOYMENT.md | ... |

## 5. Frozen Scope

До закрытия текущего milestone запрещено:
...

## 6. Codex Working Rules

Перед задачей Codex обязан читать:
1. AGENT.md
2. docs/PROJECT_CONTROL.md
3. docs/CURRENT_MILESTONE.md
4. relevant domain spec

## 7. Definition of Done

...

## 8. How to Add New Work

...

## 9. How to Close a Milestone

...
```

---

# 11. Phase 4 — Create / update canonical docs

Создать или обновить канонические документы.

## 11.1. `docs/CURRENT_STATUS.md`

Должен фиксировать правду:

```text
Фактический уровень:
v0.4-alpha foundation

Есть:
- personal dashboard;
- rule-based problem detection;
- recommendation tracking;
- AI coach handoff;
- Steam import scaffold.

Не готово:
- secure friends alpha;
- public beta;
- reliable metric truth layer;
- production-ready Steam auto sync;
- mature AI coach loop.
```

## 11.2. `docs/VERSION_MAP.md`

Таблица:

```markdown
| Version | Name | Status | Evidence | Blockers |
|---|---|---|---|---|
| v0.1 | Personal Dashboard | done | ... | ... |
| v0.2 | Problem Detection | partial | ... | ... |
| v0.3 | Recommendation Engine | partial | ... | ... |
| v0.4 | Tracking Loop | partial | ... | ... |
| v0.5 | Map/Side Deep Dive | started | ... | ... |
| v0.6 | AI Coach Summary | partial | ... | ... |
| v0.7 | Secure Friends Alpha | blocked | ... | ... |
```

## 11.3. `docs/CURRENT_MILESTONE.md`

Текущий milestone:

```text
v0.7-prep: Secure Single/Friends Alpha + Honest Coach Loop
```

С подэтапами:

1. Freeze scope.
2. Test isolation.
3. Security P0.
4. Ownership/single-user mode.
5. Steam cursor truth.
6. Metric truth.
7. Parser hardening.
8. Diagnosis registry.
9. Recommendation planner.
10. Structured AI.
11. Coach-first UI.

## 11.4. `docs/ROADMAP.md`

Упорядочить roadmap:

```text
v0.4.1 Scope Freeze
v0.4.2 Test Isolation + Backup
v0.4.3 Security P0
v0.4.4 Ownership Foundation
v0.4.5 Steam Cursor Truth
v0.4.6 Metric Truth Layer
v0.4.7 Parser Hardening
v0.5 Diagnosis Engine v1
v0.6 Recommendation Planner v1
v0.6.1 Structured AI Coach
v0.6.2 Coach-first UI
v0.7 Friends Alpha
v0.8 Feedback Calibration
v1.0 Public Beta
```

## 11.5. `docs/METRICS.md`

Если файла нет — создать skeleton. Не надо выдумывать все формулы. Сначала зафиксировать:

- implemented;
- partial;
- best_effort;
- unavailable;
- suppressed.

## 11.6. `docs/RECOMMENDATIONS.md`

Описать target architecture:

```text
ProblemDetectionResult -> ProblemSnapshot -> PrimaryRecommendation -> MatchEvaluation -> Progress
```

## 11.7. `docs/SECURITY.md`

Описать:

- current risks;
- public `/api/*` problem if still present;
- session secret;
- CSRF;
- ownership;
- registration policy;
- upload limits;
- friends alpha blockers.

## 11.8. `docs/STEAM_IMPORT.md`

Обязательно включить:

```text
Steam OpenID gives steam_id only.
Steam service bot can resolve share code -> match_time + demo_url.
Automatic match history sync needs user Game Authentication Code + knowncode cursor.
knowncode=0 can return HTTP 412.
UI must diagnose cursor freshness.
Stale cursor must not trigger old history download.
```

## 11.9. `docs/AI_COACH.md`

Описать:

- AI is explanation layer, not source of truth;
- structured output target;
- prompt versioning;
- validator;
- fallback.

## 11.10. `AGENT.md`

Создать/обновить.

Содержимое:

```markdown
# AGENT.md — rules for Codex/AI agents

## Before any work
1. Read docs/PROJECT_CONTROL.md.
2. Read docs/CURRENT_MILESTONE.md.
3. Read the relevant domain doc.
4. Run git status.
5. Do not add features outside current milestone.

## Hard bans
- no viewer;
- no heatmaps;
- no clips;
- no new AI providers;
- no Steam/FACEIT expansion;
- no public/friends features before security/ownership.

## Required after work
- tests;
- docs update;
- changelog;
- git commit.
```

---

# 12. Phase 5 — Deprecation plan

Создать:

```text
docs/audit/DOCUMENT_DEPRECATION_PLAN.md
```

Для устаревших документов:

```markdown
| Old file | Problem | Superseded by | Action |
|---|---|---|---|
```

Действия:

```text
keep_as_history
mark_deprecated_header
move_to_archive
merge_then_archive
delete_later_after_review
```

Не удалять документы сразу. Сначала пометить.

Deprecated header:

```markdown
> STATUS: DEPRECATED / HISTORICAL
> Superseded by: docs/PROJECT_CONTROL.md and docs/...
> Do not use this file as current instruction.
```

---

# 13. Phase 6 — README cleanup

README должен стать коротким входом, а не складом всех мыслей.

README структура:

```markdown
# CS2 AI Coach

## What it is
...

## Current status
See docs/CURRENT_STATUS.md

## How to run
...

## How to test
...

## Main documentation
See docs/PROJECT_CONTROL.md

## Current limitations
See docs/KNOWN_LIMITATIONS.md
```

Не надо держать весь roadmap в README.

---

# 14. Phase 7 — Final checks

Перед завершением:

```bash
git status --short
git diff --stat
```

Проверить:

1. Код не изменён.
2. БД не изменена.
3. Созданы только docs/AGENT/LATER/README changes.
4. Старые файлы не удалены без плана.
5. Есть единый source of truth.
6. Есть audit report.
7. Есть deprecation plan.

Если случайно изменён код — остановиться и явно сообщить.

---

# 15. Итоговые артефакты

После выполнения должны быть:

```text
docs/audit/INSTRUCTIONS_AUDIT_REPORT.md
docs/audit/INSTRUCTIONS_INVENTORY.md
docs/audit/DOCUMENT_CONFLICTS.md
docs/audit/DOCUMENT_DEPRECATION_PLAN.md

docs/PROJECT_CONTROL.md
docs/CURRENT_STATUS.md
docs/VERSION_MAP.md
docs/CURRENT_MILESTONE.md
docs/ROADMAP.md
docs/METRICS.md
docs/RECOMMENDATIONS.md
docs/SECURITY.md
docs/STEAM_IMPORT.md
docs/AI_COACH.md
docs/TESTING.md
docs/DEPLOYMENT.md
docs/BACKUP_RESTORE.md
docs/KNOWN_LIMITATIONS.md
docs/RELEASE_CHECKLIST.md
docs/DECISIONS.md
docs/CHANGELOG.md

AGENT.md
LATER.md
```

Если какие-то файлы уже есть — обновить и объединить, а не плодить дубли.

---

# 16. Финальный отчёт Codex

В конце написать:

```text
Аудит и консолидация инструкций завершены.

Что сделано:
...

Главный source of truth:
docs/PROJECT_CONTROL.md

Что читать Codex перед работой:
1. AGENT.md
2. docs/PROJECT_CONTROL.md
3. docs/CURRENT_MILESTONE.md
4. relevant domain doc

Какие документы устарели:
...

Какие конфликты были найдены:
...

Что осталось проверить вручную:
...

Код проекта не изменялся / изменялся только docs.
```

---

# 17. Стартовый промпт для Codex CLI

Скопировать из корня проекта:

```text
Проведи аудит и консолидацию всех инструкций проекта по файлу INSTRUCTIONS_CONSOLIDATION_TASK.md.

Главная цель:
свести README, docs, instructions, roadmap, audit-файлы и agent-rules в единую систему документации, где есть один главный source of truth: docs/PROJECT_CONTROL.md.

Важно:
- не меняй код приложения;
- не меняй БД;
- не запускай импорт/Steam/parser jobs;
- не удаляй старые документы без deprecation plan;
- сначала сделай inventory и conflict audit;
- потом создай/обнови canonical docs;
- старые конфликтующие документы пометь как historical/deprecated только после анализа.

Обязательные результаты:
1. docs/audit/INSTRUCTIONS_INVENTORY.md
2. docs/audit/DOCUMENT_CONFLICTS.md
3. docs/audit/DOCUMENT_DEPRECATION_PLAN.md
4. docs/PROJECT_CONTROL.md
5. AGENT.md
6. docs/CURRENT_STATUS.md
7. docs/CURRENT_MILESTONE.md
8. docs/VERSION_MAP.md
9. docs/ROADMAP.md
10. LATER.md

После завершения покажи git diff --stat и краткий отчёт.
```

