# CS2 AI Coach — Stabilization Stage 0 / Safety Foundation TZ

Дата: 2026-07-03  
Назначение: начать стабилизацию проекта после полного read-only аудита.  
Фокус: не новые фичи, а порядок, безопасность данных и воспроизводимые проверки.

---

# 1. Главный вывод

Проект нельзя дальше развивать как обычный feature project. Его нужно перевести в режим controlled hardening.

Фактический уровень продукта:

```text
v0.4-alpha foundation
```

Текущий milestone разработки:

```text
v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop
```

Первый разрешённый этап:

```text
Hardening Stage 0: docs baseline + backup/restore + test isolation
```

До закрытия Stage 0 запрещено:

- запускать общий pytest;
- запускать импорт;
- запускать Steam jobs;
- запускать parser jobs;
- менять production DB;
- делать миграции;
- добавлять viewer/heatmaps/clips/FACEIT/friends/public/social/payments;
- начинать Metric Truth Layer;
- начинать Security P0 правки, если нет backup/restore и test isolation.

---

# 2. Почему Stage 0 обязателен

Аудит показал:

1. Рабочее дерево уже dirty: много docs/instructions modified и untracked canonical/audit files.
2. Runtime data не трогались, но в проекте есть `data/*.db` и `.env`.
3. Полный pytest небезопасен: `TestClient(app)` может импортировать `app.main`, lifespan вызывает `init_db()`, global engine берётся из реального `DATABASE_URL`.
4. Backup/restore scripts не найдены.
5. DB startup использует `create_all` и ручные SQLite `ALTER`.
6. Без проверенного backup/restore и test isolation любые P0 security-правки могут испортить рабочую БД или дать ложное ощущение стабильности.

---

# 3. Stage 0 DoD

Stage 0 считается закрытым только если:

## 3.1. Git / docs baseline

- `git status --short` понятен.
- Все изменения документации после консолидации просмотрены.
- Документационный baseline зафиксирован отдельным commit или явно оставлен uncommitted по решению пользователя.
- Нет смешивания docs-only изменений с code-hardening изменениями.

## 3.2. Backup/restore

- Есть скрипт backup для `data/cs2_coach.db` и runtime artifacts.
- Backup создаётся в отдельную директорию, например `backups/`.
- Backup не попадает в git.
- Restore проверен на копии, не на production DB.
- Есть `docs/BACKUP_RESTORE.md` с реальной процедурой.
- Есть команда проверки, что backup существует.

## 3.3. Test isolation

- Есть test environment, который не может использовать `data/cs2_coach.db`.
- Есть safe test command.
- Есть fail-fast guard: если `APP_ENV=test`, но DB указывает на production path, тесты падают.
- `TestClient(app)` не мутирует production DB.
- General pytest безопасен или явно запрещён до следующего этапа.
- `docs/TESTING.md` обновлён реальной процедурой.

## 3.4. No runtime jobs

- Не запускались import jobs.
- Не запускались Steam jobs.
- Не запускались parser jobs.
- Не запускались опасные тесты.
- Production DB не изменялась без backup.

---

# 4. Рабочий порядок Stage 0

## Step 0 — Preflight

Выполнить:

```bash
pwd
whoami
git branch --show-current
git status --short
git diff --stat
git log --oneline -10
```

Задача: понять, что уже изменено после документационных проходов.

## Step 1 — Зафиксировать документационный baseline

Сначала показать пользователю:

```bash
git diff --stat
git status --short
```

Если изменения только в docs/instructions/AGENT/LATER/README/audit:

- предложить commit:

```bash
git add AGENT.md README.md LATER.md docs instructions
git commit -m "Consolidate project control documentation"
```

Если есть изменения в `app/`, `data/`, `.env`, migrations, tests — остановиться и запросить решение пользователя.

## Step 2 — Создать hardening branch

```bash
git checkout -b hardening/stage-0-safety-foundation
```

Если ветка есть:

```bash
git checkout hardening/stage-0-safety-foundation
```

## Step 3 — Backup/restore design

Создать:

```text
scripts/backup_runtime.sh
scripts/restore_runtime.sh
docs/BACKUP_RESTORE.md
```

Backup должен включать:

```text
data/cs2_coach.db
data/reports/
data/uploads/
важные runtime artifacts, если они есть
```

Backup должен исключать:

```text
.env secrets unless explicitly approved
raw large .dem files unless policy says include
```

Минимальная безопасная стратегия:

```bash
mkdir -p backups
sqlite3 data/cs2_coach.db ".backup 'backups/cs2_coach_YYYYMMDD_HHMMSS.db'"
tar -czf backups/runtime_YYYYMMDD_HHMMSS.tar.gz data/reports data/uploads 2>/dev/null || true
```

Restore проверять только на копии:

```bash
cp backups/cs2_coach_*.db /tmp/cs2_coach_restore_test.db
sqlite3 /tmp/cs2_coach_restore_test.db "PRAGMA integrity_check;"
```

## Step 4 — Test isolation design

Нужно найти, где создаётся DB engine и как тесты импортируют приложение.

Проверить:

```bash
rg "DATABASE_URL|SessionLocal|create_engine|init_db|TestClient|lifespan|data/cs2_coach.db" app tests
```

Нужно добиться:

- tests используют temp/in-memory DB;
- web smoke tests не используют production settings;
- app startup в тестах не делает production schema upgrade;
- есть `APP_ENV=test`;
- есть guard against production DB path.

## Step 5 — Safe test command

Пример целевого результата:

```bash
APP_ENV=test DATABASE_URL=sqlite:////tmp/jc-coach-test.db pytest tests -q
```

Но фактическая команда должна быть выбрана по коду проекта.

Обязательное условие:

```text
safe test command cannot read/write data/cs2_coach.db
```

## Step 6 — Documentation update

Обновить:

```text
docs/TESTING.md
docs/BACKUP_RESTORE.md
docs/CURRENT_MILESTONE.md
docs/CHANGELOG.md
```

## Step 7 — Verification

Перед завершением показать:

```bash
git status --short
git diff --stat
```

Если тесты уже безопасны, можно запускать только safe tests.

Если test isolation ещё не доказан, не запускать общий pytest.

---

# 5. Запрещённые действия в Stage 0

Codex не должен:

1. Исправлять `/api/*` auth.
2. Добавлять CSRF.
3. Добавлять rate limit.
4. Делать ownership.
5. Добавлять Alembic.
6. Рефакторить recommendation service.
7. Менять parser.
8. Менять Steam import.
9. Менять AI coach.
10. Улучшать UI.
11. Запускать demo parsing.
12. Запускать Steam sync.
13. Запускать импорт.
14. Запускать production server.
15. Делать общий pytest до test isolation.

Эти задачи идут позже.

---

# 6. Когда переходить к Stage 1

Переходить к Security P0 можно только если:

```text
backup/restore verified
test isolation verified
safe test command exists
production DB protected
docs updated
git status clean or intentionally staged
```

Stage 1 будет:

```text
Security P0:
- close public /api/*
- protect state-changing routes
- CSRF
- rate limits
- strong session secret fail-fast
- Steam OpenID assertion verification
- dangerous jobs auth/logging
```

---

# 7. Стартовый промпт для Codex

```text
Начни Hardening Stage 0: Safety Foundation.

Перед работой прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_MILESTONE.md
- docs/TESTING.md
- docs/BACKUP_RESTORE.md
- docs/SECURITY.md
- docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
- docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
- STABILIZATION_STAGE_0_TZ_CS2_AI_COACH.md

Цель Stage 0:
не чинить весь проект, а подготовить безопасный фундамент для будущих правок:
1. разобраться с текущим dirty git status;
2. отделить docs baseline от code hardening;
3. создать backup/restore процесс;
4. подтвердить test isolation;
5. создать safe test command;
6. обновить docs.

Жёсткие ограничения:
- не запускай импорт;
- не запускай Steam jobs;
- не запускай parser jobs;
- не запускай общий pytest до подтверждения test isolation;
- не меняй production DB без backup;
- не добавляй новые фичи;
- не трогай viewer/heatmaps/clips/FACEIT/friends/public/social/payments;
- не начинай Security P0, ownership, migrations, Metric Truth Layer, parser hardening, AI validator или UI redesign в этом этапе.

Сначала покажи:
- git status --short
- git diff --stat
- краткий план безопасных изменений

После этого реализуй только Stage 0.

В конце покажи:
- что изменено;
- какие команды запускались;
- была ли затронута production DB;
- был ли создан и проверен backup;
- подтверждён ли safe test command;
- можно ли переходить к Security P0.
```

