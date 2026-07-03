# CS2 AI Coach — Stabilization Stage 3 / Migration Discipline TZ

Дата: 2026-07-03  
Назначение: отдельное ТЗ для Stage 3 после закрытия Stage 2 Ownership / enforced single-owner boundaries.  
Фокус: прекратить бесконтрольную эволюцию схемы БД и ввести проверяемую migration discipline без повреждения production SQLite.

---

# 1. Статус перед Stage 3

Stage 3 можно начинать только если:

```text
[✓] Stage 0 Safety Foundation committed
[✓] Stage 1 Security P0 committed
[✓] Stage 2 Ownership / enforced single-owner boundaries committed
[✓] git status clean
[✓] production DB SHA known
```

Перед стартом выполнить:

```bash
cd /opt/jc-coach
git status --short
git log --oneline -5
sha256sum data/cs2_coach.db
```

Ожидаемый текущий верхний commit:

```text
Add enforced single-owner boundaries
```

Если `git status --short` не пустой — Stage 3 не начинать.

---

# 2. Почему Stage 3 нужен

По full audit в проекте остаётся P1/P0 architectural debt:

```text
- SQLite production DB живёт в data/cs2_coach.db
- app startup вызывает Base.metadata.create_all(bind=engine)
- есть manual SQLite ALTER / _upgrade_sqlite_schema()
- нет Alembic или другого явного migration ledger
- schema evolution может происходить на startup неявно
- backup/restore уже есть, но schema changes пока не управляются формально
```

Это опасно перед следующими этапами, потому что:

```text
Recommendation read/write split
Metric Truth Layer
Parser hardening
Steam cursor truth
AI validator
```

почти наверняка потребуют новых таблиц/полей. Без migration discipline каждый следующий stage будет потенциально ломать production DB.

---

# 3. Главная цель Stage 3

Ввести минимальную, безопасную и проверяемую discipline для изменений схемы БД.

Цель не в том, чтобы сразу идеально мигрировать весь legacy, а в том, чтобы после Stage 3 было ясно:

```text
1. какая схема сейчас считается baseline;
2. как добавляются будущие schema changes;
3. какие startup schema mutations остаются legacy;
4. как перед DB change делается backup;
5. как проверяется migration на копии DB;
6. какой safe command использовать в тестах/CI.
```

---

# 4. Не цель Stage 3

Запрещено в Stage 3:

- менять бизнес-логику coach/recommendations/metrics/parser/Steam;
- делать Metric Truth Layer;
- делать recommendation read/write split;
- делать parser hardening;
- делать AI validator;
- делать UI redesign;
- добавлять SaaS/friends/public features;
- запускать production import/Steam/parser jobs;
- менять production DB без explicit backup + dry-run/restore procedure;
- делать большой data migration;
- массово добавлять `user_id` в core tables;
- удалять legacy schema upgrade code без доказанного replacement.

Если Codex считает, что для Stage 3 нужна destructive migration или production DB mutation — он должен остановиться и написать `BLOCKED`.

---

# 5. Preferred implementation direction

Предпочтительный путь:

```text
Alembic-based migration discipline with current schema baseline
```

Но с ограничением:

```text
не применять миграции к production DB без отдельного explicit command и backup.
```

Возможные приемлемые результаты Stage 3:

## Option A — full minimal Alembic setup

- добавить Alembic config;
- создать baseline revision, отражающую текущую модель/схему;
- добавить safe scripts:
  - check current migration status;
  - run migrations on temp copy;
  - generate migration only manually;
- tests подтверждают, что test DB может создаваться/мигрироваться без production DB;
- docs описывают процесс.

## Option B — migration discipline scaffold без применения Alembic

Если текущая архитектура мешает безопасно включить Alembic за один stage:

- создать migration policy docs;
- создать schema inventory;
- добавить scripts для DB schema dump / schema compare / dry-run copy verification;
- пометить startup `_upgrade_sqlite_schema()` as legacy;
- сделать `BLOCKED` или `PASS_WITH_WARNINGS` с точным планом Stage 3B.

Но предпочтение — Option A, если это безопасно.

---

# 6. Stage 3 tasks

## 6.1. Audit current DB schema handling

Найти:

```bash
rg -n "create_all|metadata|upgrade_sqlite|ALTER TABLE|PRAGMA|sqlite|migration|migrate|alembic" app tests docs scripts
```

Составить краткий inventory:

```text
docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md
```

В нём зафиксировать:

- где создаётся schema;
- где startup может менять schema;
- какие manual upgrades существуют;
- какие риски;
- что остаётся legacy после Stage 3;
- что является новым migration path.

## 6.2. Decide migration policy

Документировать:

```text
docs/MIGRATIONS.md
```

Минимум:

- production DB никогда не меняется без backup;
- migration сначала проверяется на копии;
- startup schema mutations запрещены для новых изменений;
- new schema changes must be migration-first;
- tests run on isolated temp DB;
- rollback/restore path;
- how to inspect current schema;
- how to create a new migration;
- how to apply migration safely.

## 6.3. Add migration tooling

Если выбран Alembic:

Добавить:

```text
alembic.ini
alembic/env.py
alembic/versions/<baseline>.py
scripts/migration_status.sh
scripts/migration_check_on_copy.sh
```

Требования:

- Alembic должен читать settings/database URL безопасно;
- test env не должен использовать production DB;
- baseline не должен мутировать production DB автоматически;
- scripts должны быть safe-by-default;
- dangerous production apply требует явного env flag, например:
  `ALLOW_PRODUCTION_MIGRATION=1`.

Если Alembic уже установлен в окружении — использовать его.  
Если нет — не ломать venv неконтролируемо. Проверить dependency management проекта и действовать минимально.

## 6.4. Startup schema mutation policy

Проверить current startup behavior.

Если сейчас есть:

```text
Base.metadata.create_all(bind=engine)
_upgrade_sqlite_schema()
```

Не обязательно удалять сразу, если это сломает app. Но нужно:

- зафиксировать, что это legacy compatibility path;
- запретить добавлять туда новые schema changes;
- если безопасно — ограничить его local/test режимом;
- если небезопасно менять сейчас — оставить как documented risk.

Acceptance:

```text
[ ] new docs say: no new schema changes through startup upgrade helper
[ ] tests still pass
[ ] existing production DB not changed
```

## 6.5. Tests

Добавить/обновить tests, например:

```text
tests/test_migrations.py
```

Минимум:

1. test settings cannot target production DB in `APP_ENV=test`.
2. migration/status/check command works on temp DB or temp copy.
3. schema tooling does not mutate production DB.
4. if Alembic baseline exists, it can be inspected/imported.
5. existing app tests still pass.

Не надо делать destructive migration tests на production DB.

## 6.6. Docs update

Обновить:

```text
docs/PROJECT_CONTROL.md
docs/CURRENT_STATUS.md
docs/CURRENT_MILESTONE.md
docs/ROADMAP.md если есть stage status list
docs/BACKUP_RESTORE.md
docs/TESTING.md
docs/RELEASE_CHECKLIST.md
docs/CHANGELOG.md
```

Создать:

```text
docs/MIGRATIONS.md
docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md
docs/audit/STAGE_3_MIGRATION_IMPLEMENTATION_REPORT.md
```

---

# 7. Safe checks

Запустить:

```bash
APP_ENV=test .venv/bin/pytest tests/test_migrations.py -q
APP_ENV=test .venv/bin/pytest tests -q
.venv/bin/ruff check .
git diff --check
sha256sum data/cs2_coach.db
```

Если добавлены shell scripts:

```bash
bash -n scripts/migration_status.sh
bash -n scripts/migration_check_on_copy.sh
```

Если Alembic добавлен:

```bash
APP_ENV=test .venv/bin/alembic current
```

или documented equivalent safe command.

---

# 8. Production DB safety rule

Stage 3 должен сохранить production DB SHA unchanged, если только пользователь явно не разрешил mutation.

Current known hash before Stage 3:

```text
b9c25d93f0a73e9b4e5e4597d93c90021800edb50375acdd335fc9558b276b3c
```

Если hash меняется без явного разрешения — Stage 3 FAIL/BLOCKED.

---

# 9. Stage 3 DoD

Stage 3 считается реализованным только если:

```text
[ ] current schema evolution inventory created
[ ] migration policy documented
[ ] safe migration tooling added or clear BLOCKED reason documented
[ ] production DB not mutated
[ ] backup-before-migration procedure documented
[ ] future schema changes have explicit migration path
[ ] startup schema mutations are documented as legacy or constrained
[ ] safe migration/check tests added
[ ] existing tests pass
[ ] ruff passes
[ ] git diff --check passes
[ ] import/Steam/parser production jobs not run
[ ] Stage 3 implementation report created
```

---

# 10. Start prompt for Codex

```text
Начни Stage 3: Migration discipline.

Главный файл задания:
docs/tasks/STABILIZATION_STAGE_3_MIGRATION_DISCIPLINE_TZ_CS2_AI_COACH.md

Перед работой обязательно прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/BACKUP_RESTORE.md
- docs/TESTING.md
- docs/SECURITY.md
- docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
- docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
- docs/audit/STAGE_1_SECURITY_P0_REVIEW.md
- docs/audit/STAGE_2_OWNERSHIP_REVIEW.md
- docs/tasks/STABILIZATION_STAGE_3_MIGRATION_DISCIPLINE_TZ_CS2_AI_COACH.md

Stage 0 Safety Foundation завершён и закоммичен.
Stage 1 Security P0 завершён и закоммичен.
Stage 2 Ownership / enforced single-owner boundaries завершён и закоммичен.

Сначала покажи:
- git status --short
- git diff --stat
- git log --oneline -5
- sha256sum data/cs2_coach.db
- краткий план изменений по файлам

Цель Stage 3:
ввести migration discipline для будущих schema changes без повреждения production SQLite DB.

Нужно:
1. провести audit текущей schema evolution логики:
   - create_all
   - _upgrade_sqlite_schema
   - manual ALTER/PRAGMA
   - sqlite/session/init_db behavior
2. создать docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md
3. создать docs/MIGRATIONS.md
4. добавить safe migration tooling:
   - предпочтительно Alembic baseline + safe scripts;
   - если Alembic небезопасно включить за один stage, сделать documented scaffold и BLOCKED/PASS_WITH_WARNINGS с точным follow-up.
5. не применять миграции к production DB без explicit approval.
6. добавить tests/test_migrations.py или equivalent safe tests.
7. обновить docs:
   - docs/PROJECT_CONTROL.md
   - docs/CURRENT_STATUS.md
   - docs/CURRENT_MILESTONE.md
   - docs/BACKUP_RESTORE.md
   - docs/TESTING.md
   - docs/RELEASE_CHECKLIST.md
   - docs/CHANGELOG.md
8. создать docs/audit/STAGE_3_MIGRATION_IMPLEMENTATION_REPORT.md

Жёсткие ограничения:
- не менять coach/recommendation/metric/parser/Steam/AI/UI behavior;
- не делать Metric Truth Layer;
- не делать recommendation read/write split;
- не делать parser hardening;
- не делать AI validator;
- не запускать import/Steam/parser production jobs;
- не менять production DB без explicit backup and approval;
- не делать destructive migrations;
- не делать commit.

Проверки:
- APP_ENV=test .venv/bin/pytest tests/test_migrations.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db
- bash -n scripts/migration_status.sh, если создан
- bash -n scripts/migration_check_on_copy.sh, если создан

Финальный отчёт должен содержать:
- STAGE_RESULT: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED
- migration approach chosen
- production DB touched: yes/no
- DB SHA before/after
- files changed
- tests added
- safe checks results
- remaining risks
- can proceed to Stage 3 review-only: yes/no

Если считаешь, что нужно менять production DB или делать destructive migration — остановись и напиши BLOCKED.
```

---

# 11. Review-only prompt

После implementation обязательно отдельный review-only pass:

```text
Проведи review-only проверку Stage 3 Migration discipline.

Ничего не меняй в коде, тестах и документации, кроме создания одного review-отчёта:
docs/audit/STAGE_3_MIGRATION_REVIEW.md

Не запускай import/Steam/parser jobs.
Не делай commit.
Не переходи к Stage 4.

Прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/MIGRATIONS.md
- docs/BACKUP_RESTORE.md
- docs/audit/DB_SCHEMA_EVOLUTION_INVENTORY.md
- docs/audit/STAGE_3_MIGRATION_IMPLEMENTATION_REPORT.md
- текущий git diff, включая untracked files

Проверь Stage 3 DoD:
1. current schema evolution inventory exists and is accurate;
2. migration policy documented;
3. safe migration tooling exists or BLOCKED reason is explicit;
4. production DB SHA unchanged;
5. backup-before-migration procedure documented;
6. startup schema mutations are documented as legacy or constrained;
7. future schema changes have explicit migration path;
8. tests added;
9. full safe pytest passes;
10. ruff passes;
11. git diff --check passes;
12. import/Steam/parser production jobs not run;
13. no coach/recommendation/metric/parser/Steam/AI/UI behavior changes.

Запусти:
- APP_ENV=test .venv/bin/pytest tests/test_migrations.py -q
- APP_ENV=test .venv/bin/pytest tests -q
- .venv/bin/ruff check .
- git diff --check
- sha256sum data/cs2_coach.db
- bash -n scripts/migration_status.sh, если создан
- bash -n scripts/migration_check_on_copy.sh, если создан

Создай docs/audit/STAGE_3_MIGRATION_REVIEW.md:

# Stage 3 Migration Review

## STAGE_RESULT
PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

## Evidence by DoD Item

## Migration Approach Review

## Changed Files Reviewed

## Test Results

## Production DB Check

## Import/Steam/Parser Jobs Check

## Remaining Risks

## Must Fix Before Stage 4

## Can Proceed To Stage 4
yes/no

Если Stage 3 не проходит — не исправляй, только напиши, что именно не проходит.
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
git add app docs tests scripts alembic alembic.ini pyproject.toml requirements.txt
git commit -m "Add migration discipline"
```

Adjust `git add` if some paths do not exist.

После commit:

```bash
git status --short
git log --oneline -5
```

---

# 13. After Stage 3

Следующий этап после Stage 3:

```text
Stage 4: Recommendation read/write split
```

Не начинать Stage 4 без:

```text
Stage 3 implementation → review-only → repair if needed → commit
```

