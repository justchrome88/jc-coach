# FULL_PROJECT_AUDIT_AFTER_DOCS_TASK.md

ТЗ для Codex CLI: полный аудит CS2 AI Coach после консолидации документации

Дата: 2026-07-03  
Проект: CS2 AI Coach / `/opt/jc-coach`  
Режим: read-only audit  
Главная цель: провести новый полный аудит проекта уже по актуальной канонической документации, а не по старым roadmap/instructions.

---

# 0. Контекст

Документация проекта была консолидирована. Главным source of truth должен быть:

```text
docs/PROJECT_CONTROL.md
```

Codex должен считать старые `instructions/*`, старые roadmap-файлы, старые prompt libraries и исторические audit-файлы подчинёнными новой документации.

Этот аудит нужен не для исправления кода, а для создания честного текущего снимка проекта:

```text
что реально работает;
что только выглядит готовым;
что противоречит новой документации;
что опасно;
что нужно править первым;
какой следующий технический milestone;
какое ТЗ на правки надо составить после аудита.
```

---

# 1. Главный приказ Codex

Проведи полный аудит проекта.

Не исправляй проект.

Не меняй код.

Не меняй БД.

Не запускай опасные тесты.

Не запускай import/Steam/parser jobs.

Создай полный отчёт:

```text
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
```

Если нужны дополнительные отчёты, можно создать:

```text
docs/audit/FULL_PROJECT_AUDIT_SCORECARD.md
docs/audit/FULL_PROJECT_AUDIT_FINDINGS.md
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
```

Но главный файл обязателен.

---

# 2. Жёсткие ограничения

## 2.1. Запрещено

1. Менять код приложения.
2. Менять БД.
3. Менять миграции.
4. Менять `.env`.
5. Удалять файлы.
6. Запускать Steam sync.
7. Запускать DEM parser jobs.
8. Запускать import jobs.
9. Запускать тесты, если test isolation не подтверждён.
10. Делать git commit.
11. Писать “всё хорошо” без доказательств.
12. Считать старые инструкции актуальными, если они противоречат `docs/PROJECT_CONTROL.md`.

## 2.2. Разрешено

1. Читать файлы.
2. Смотреть структуру проекта.
3. Смотреть git status/log.
4. Искать code smells, TODO/FIXME, hardcoded values.
5. Читать canonical docs.
6. Читать код.
7. Читать тесты.
8. Делать статический анализ.
9. Запускать только заведомо безопасные команды.
10. Создать audit-файлы в `docs/audit/`.

---

# 3. Языковое правило

Все новые человекочитаемые отчёты писать на русском языке.

Можно оставлять на английском:

- имена файлов;
- команды;
- endpoint-ы;
- имена классов/функций;
- enum/status values;
- code blocks;
- technical identifiers.

Не переписывать существующую документацию на английский.

---

# 4. Канонические документы, которые нужно прочитать первыми

Перед анализом кода прочитать:

```text
AGENT.md
docs/PROJECT_CONTROL.md
docs/CURRENT_STATUS.md
docs/CURRENT_MILESTONE.md
docs/VERSION_MAP.md
docs/ROADMAP.md
docs/ARCHITECTURE.md
docs/METRICS.md
docs/RECOMMENDATIONS.md
docs/SECURITY.md
docs/STEAM_IMPORT.md
docs/AI_COACH.md
docs/TESTING.md
docs/BACKUP_RESTORE.md
docs/KNOWN_LIMITATIONS.md
docs/RELEASE_CHECKLIST.md
docs/audit/INSTRUCTIONS_VALIDATION_REPORT.md
docs/audit/DOCUMENT_CONFLICTS.md
docs/audit/DOCUMENT_DEPRECATION_PLAN.md
```

Если какого-то файла нет — зафиксировать в отчёте, но не создавать его в рамках аудита, если это не audit-файл.

---

# 5. Главная логика оценки

Оцени проект относительно двух осей:

## 5.1. Фактический уровень продукта

Ожидаемая формулировка:

```text
Фактический уровень: v0.4-alpha foundation
```

То есть уже есть:

- personal dashboard;
- basic problem detection;
- recommendation tracking skeleton;
- AI coach handoff/scaffold;
- Steam import scaffold.

Но ещё не готово:

- secure friends alpha;
- public beta;
- fully reliable metric truth;
- production-ready Steam auto sync;
- mature AI coach loop.

## 5.2. Текущий milestone разработки

Ожидаемая формулировка:

```text
Текущий milestone: v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop
```

То есть текущая работа должна вести к:

- test isolation;
- backup;
- security P0;
- ownership;
- Steam cursor truth;
- Metric Truth Layer;
- parser hardening;
- diagnosis registry;
- recommendation planner;
- structured AI;
- coach-first UI.

---

# 6. Stage 0 — Read-only preflight

Выполнить безопасные команды:

```bash
pwd
whoami
git status --short
git branch --show-current || true
git log --oneline -10 || true
find . -maxdepth 2 -type f | sort | sed 's#^\./##' | head -300
```

Дополнительно:

```bash
find docs instructions tests app -maxdepth 3 -type f 2>/dev/null | sort | head -500
```

Не запускать приложение.

Не запускать тесты.

Не запускать импорт.

Результат Stage 0:

- путь проекта;
- пользователь;
- ветка;
- git status;
- последние commits;
- стек;
- крупные директории;
- видимые риски;
- можно ли безопасно продолжать audit.

---

# 7. Stage 1 — Documentation-to-code alignment audit

Проверь, соответствует ли код тому, что заявлено в канонической документации.

## 7.1. Проверить соответствие

| Область | Canonical doc | Что проверить в коде |
|---|---|---|
| Project status | CURRENT_STATUS / VERSION_MAP | не завышен ли статус |
| Current milestone | CURRENT_MILESTONE | работает ли код в направлении milestone |
| Architecture | ARCHITECTURE.md | реально ли слои разделены |
| Metrics | METRICS.md | есть ли formula/source/reliability в коде |
| Recommendations | RECOMMENDATIONS.md | есть ли problem -> recommendation loop |
| Security | SECURITY.md | закрыты ли API/auth/CSRF/ownership |
| Steam | STEAM_IMPORT.md | есть ли cursor freshness diagnostics |
| AI | AI_COACH.md | есть ли schema/validator/fallback |
| Testing | TESTING.md | test isolation подтверждён или нет |
| Backup | BACKUP_RESTORE.md | есть ли реальные scripts/process |

## 7.2. Вывести таблицу

```markdown
| Doc claim | Code reality | Status | Evidence | Risk | Fix priority |
|---|---|---|---|---|---|
```

Статусы:

```text
match
partial
mismatch
not_implemented
unknown
```

---

# 8. Stage 2 — Architecture audit

Оцени архитектуру по слоям:

```text
Data/import layer
Parser facts layer
Metric engine
Metric truth/reliability layer
Diagnosis engine
Recommendation planner
Recommendation evaluator
AI coach layer
Web UI
API
Auth/security
Testing
Deployment/ops
Documentation/process
```

Для каждого слоя:

```markdown
| Layer | Score 0-5 | Status | Evidence | Main problems | Required fixes |
|---|---:|---|---|---|---|
```

Score:

```text
0 — отсутствует
1 — наброски
2 — частично, хрупко
3 — MVP работает, но есть долг
4 — хорошо структурировано
5 — зрелый уровень
```

Статусы:

```text
🟢 нормально
🟡 долг
🔴 критично
⚫ не обнаружено
```

---

# 9. Stage 3 — Security audit

Проверить строго.

## 9.1. Обязательные вопросы

1. Открыт ли `/api/*` без auth?
2. Какие endpoints public?
3. Есть ли server-side auth?
4. Есть ли default session secret?
5. Есть ли fail-fast для default secret в non-local env?
6. Есть ли CSRF для POST forms?
7. Есть ли rate limit для login/upload/AI/Steam endpoints?
8. Есть ли user ownership?
9. Есть ли `user_id` на `Match`, recommendations, reports, jobs, steam accounts?
10. Фильтруются ли queries по current user?
11. Может ли один пользователь увидеть чужие данные?
12. Есть ли upload size limits?
13. Есть ли safe temp file cleanup?
14. Есть ли `.env` в git?
15. Есть ли secrets в репозитории?
16. Есть ли публичные debug endpoints?
17. Готов ли проект к friends alpha?
18. Готов ли проект к public beta?

## 9.2. Итог

```markdown
## Security Verdict

Personal local: yes/no
Personal remote behind VPN/basic auth: yes/no
Friends alpha: yes/no
Public beta: yes/no

P0 blockers:
...
```

---

# 10. Stage 4 — Database and migration audit

Проверить:

1. SQLite или другая БД.
2. Есть ли Alembic/migrations.
3. Есть ли manual `CREATE/ALTER` в runtime.
4. Вызывает ли app startup `init_db()` и может ли менять production schema.
5. Есть ли backup scripts.
6. Есть ли restore scripts.
7. Есть ли DB versioning.
8. Есть ли test database isolation.
9. Есть ли риск, что pytest тронет production DB.
10. Есть ли runtime data в git.

Вывести:

```markdown
| Risk | Evidence | Severity | Fix |
|---|---|---|---|
```

---

# 11. Stage 5 — Test isolation audit

Не запускать тесты, пока не подтверждено, что они безопасны.

Проверить статически:

1. Как создаётся test client.
2. Как выбирается DATABASE_URL.
3. Используются ли temp DB fixtures.
4. Импортирует ли test `app.main` с lifespan/init_db.
5. Могут ли tests писать в `data/cs2_coach.db`.
6. Есть ли `APP_ENV=test`.
7. Есть ли pytest fixtures for DB isolation.
8. Есть ли CI или test script.

Итог:

```text
Tests safe to run: yes/no/unknown
Reason:
...
```

Если safe — можно предложить список safe tests, но не запускать без отдельного разрешения.

---

# 12. Stage 6 — Steam import audit

Оценить с учётом свежей правды:

```text
OpenID дает steam_id only.
Автоматический sync требует Game Authentication Code + knowncode cursor.
knowncode=0 может возвращать HTTP 412.
Cursor freshness must be diagnosed.
Stale cursor must not download old history blindly.
```

Проверить:

1. Есть ли UI для ввода Game Authentication Code.
2. Есть ли UI для ввода knowncode/latest share code.
3. Есть ли диагностика свежести cursor.
4. Показывает ли приложение дату latest share code.
5. Предупреждает ли о stale cursor.
6. Не скачивает ли историю старее последнего локального матча.
7. Есть ли service bot flow.
8. Есть ли rate limit/retry.
9. Есть ли job status.
10. Есть ли owner/user scoping for Steam accounts/jobs.
11. Есть ли безопасное хранение Steam API key.
12. Есть ли понятный user-facing status: ready/stale/missing_code/error.

Итог:

```text
Steam auto import readiness:
not_ready / alpha / personal_ready / friends_ready / production_ready
```

---

# 13. Stage 7 — Metrics audit

Оценить не количество метрик, а честность.

## 13.1. Проверить

1. Есть ли `docs/METRICS.md`.
2. Есть ли в коде registry/definition метрик.
3. Есть ли formula/source/reliability/suppression.
4. Какие метрики показываются в UI.
5. Какие метрики используются в diagnosis.
6. Какие метрики используются в recommendations.
7. Какие метрики best-effort.
8. Какие unreliable, но выглядят как reliable.
9. Есть ли minimum sample size.
10. Есть ли confidence propagation.

## 13.2. Особое внимание

- K/D
- ADR
- KAST
- HS%
- winrate
- last 15/30
- swing score
- first death
- entry death
- early death
- trade kill
- traded death
- untraded death
- utility damage
- flash assists
- enemies flashed
- map split
- side split
- clutch
- economy

## 13.3. Таблица

```markdown
| Metric | Displayed? | Used for diagnosis? | Used for recommendation? | Reliability | Formula documented? | Evidence | Risk | Fix |
|---|---:|---:|---:|---|---:|---|---|---|
```

---

# 14. Stage 8 — Parser facts audit

Проверить, какие факты реально извлекаются из DEM/parser.

1. Round facts.
2. Player round facts.
3. Damage events.
4. Duel events.
5. Grenade events.
6. Weapon stats.
7. Tick/time fields.
8. Round start/end.
9. Side/team tracking.
10. Death time.
11. Killer/victim relation.
12. Trade relation.
13. Utility attribution.
14. Parser confidence.

Особо проверить:

```text
early_death != entry_death?
first_death separate?
trade_kill available?
traded_death available?
untraded_death available?
side split reliable?
```

---

# 15. Stage 9 — Diagnosis engine audit

Проверить:

1. Где находятся rules.
2. Есть ли registry.
3. Есть ли top-3 contract.
4. Есть ли primary_problem.
5. Есть ли confidence.
6. Есть ли sample size.
7. Есть ли suppression.
8. Есть ли effect size.
9. Есть ли recency weighting.
10. Есть ли coachability.
11. Есть ли explanation/evidence.
12. Есть ли scattered hardcoded thresholds.

Вывести:

```markdown
| Problem type | Implemented? | Evidence | Confidence | Sample guard | Suppression | Recommendation mapping | Risk |
|---|---:|---|---|---|---|---|---|
```

---

# 16. Stage 10 — Recommendation planner and tracking audit

Проверить:

1. Есть ли `ProblemSnapshot`.
2. Привязана ли recommendation к конкретной problem.
3. Есть ли одна primary active recommendation.
4. Есть ли secondary recommendations limit.
5. Есть ли baseline.
6. Есть ли target.
7. Есть ли success/failure rule.
8. Есть ли start_after_match_id.
9. Есть ли evaluation after import/job.
10. Есть ли read functions that mutate DB.
11. Есть ли recommendation progress.
12. Есть ли history.
13. Есть ли reason why selected.
14. Есть ли duplicate active recommendations.
15. Есть ли stale recommendation handling.

Ключевой запрет:

```text
GET/read helpers не должны создавать/оценивать рекомендации.
```

---

# 17. Stage 11 — AI coach audit

Проверить:

1. AI является source of truth или explanation layer.
2. Есть ли structured input.
3. Есть ли prompt version.
4. Есть ли output schema.
5. Есть ли JSON validation.
6. Есть ли binding to problem_id/recommendation_id.
7. Есть ли fallback if invalid.
8. Есть ли hallucination guard beyond prompt.
9. Есть ли storage of payload_hash/input/output.
10. Есть ли rate limit/auth for AI endpoints.
11. Есть ли риск дорогих вызовов.
12. Есть ли local LLM / Codex handoff / provider clarity.

Итог:

```text
AI coach maturity:
handoff / freeform_summary / structured_explainer / validated_coach
```

---

# 18. Stage 12 — UI/UX coach-first audit

Оценить не красоту, а тренерскую полезность.

Проверить:

1. На первом экране видно, что делать в следующих 5 матчах?
2. Есть ли primary recommendation card?
3. Есть ли why this problem?
4. Есть ли target?
5. Есть ли progress?
6. Есть ли last match coach summary?
7. Есть ли top-3 problems?
8. Есть ли reliability/suppression labels?
9. Есть ли overload metric panels?
10. Есть ли raw stats ниже, а не выше coach action?
11. Есть ли unsafe confidence language?
12. Есть ли понятное состояние Steam import.
13. Есть ли понятное состояние AI coach.

Итог:

```text
UI type:
stats_dashboard / coach_dashboard / hybrid / overloaded
```

---

# 19. Stage 13 — Ops/deployment audit

Проверить:

1. Dockerfile.
2. docker-compose.
3. systemd.
4. nginx.
5. HTTPS/basic auth/VPN assumptions.
6. logs.
7. backup.
8. restore.
9. healthcheck.
10. environment separation.
11. secrets.
12. deployment docs.
13. rollback.
14. monitoring/observability.

Итог:

```text
Deployment readiness:
local_only / personal_vps / friends_alpha / public_beta
```

---

# 20. Stage 14 — Technical debt top list

Составить top-30 technical debt.

Для каждого:

```markdown
| # | Debt | Evidence | Impact | Severity | Priority | Recommended fix |
|---:|---|---|---|---|---|---|
```

Priority:

```text
P0 — блокер безопасности/данных
P1 — блокер hardening/current milestone
P2 — важно, но не блокирует немедленно
P3 — later
```

---

# 21. Stage 15 — Roadmap correction

Сравнить реальный код с roadmap.

Ответить:

1. Можно ли начинать hardening?
2. Что должно быть первым этапом?
3. Какие задачи из roadmap преждевременны?
4. Какие задачи надо удалить/перенести в LATER?
5. Какие задачи стали актуальнее после аудита?
6. Какой следующий milestone на 7 дней?
7. Какой milestone на 14 дней?
8. Какой milestone на 30 дней?

---

# 22. Stage 16 — Draft ТЗ for fixes

В конце аудита создать черновик будущего ТЗ:

```text
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md
```

Это не полноценное ТЗ на реализацию, а список найденных правок по priority:

```markdown
# Draft Fix TZ

## P0
...

## P1
...

## P2
...

## P3
...

## Suggested implementation order
...

## Milestone 1 DoD
...

## Milestone 2 DoD
...
```

Не начинать реализацию.

---

# 23. Итоговый файл аудита

Создать:

```text
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
```

Структура:

```markdown
# Full Project Audit After Docs Consolidation

## 1. Verdict

PASS / PASS_WITH_WARNINGS / FAIL

## 2. Executive Summary

## 3. Actual Product Level vs Current Milestone

## 4. Preflight

## 5. Documentation-to-code Alignment

## 6. Architecture Scorecard

## 7. Security Audit

## 8. Database and Migration Audit

## 9. Test Isolation Audit

## 10. Steam Import Audit

## 11. Metrics Audit

## 12. Parser Facts Audit

## 13. Diagnosis Engine Audit

## 14. Recommendation Planner and Tracking Audit

## 15. AI Coach Audit

## 16. UI/UX Coach-first Audit

## 17. Ops/Deployment Audit

## 18. Technical Debt Top-30

## 19. Roadmap Correction

## 20. Must Fix Before Hardening

## 21. Can Hardening Start?

## 22. Draft Next Fix TZ Summary

## 23. Final Verdict
```

---

# 24. Критерии хорошего аудита

Хороший аудит:

1. На русском.
2. Ссылается на конкретные файлы/функции/endpoint-ы.
3. Не путает actual product level и current milestone.
4. Не доверяет старым инструкциям больше, чем PROJECT_CONTROL.
5. Не пишет “готово”, если только UI существует.
6. Отличает reliable metrics от best_effort.
7. Отличает AI handoff от validated AI coach.
8. Отличает login page от real security.
9. Отличает Steam OpenID от production-ready auto sync.
10. Даёт конкретный порядок правок.
11. Не меняет код.

Плохой аудит:

1. “В целом всё хорошо”.
2. Без evidence.
3. Без путей к файлам.
4. Без score.
5. Без P0/P1.
6. Без итогового next TZ draft.
7. С исправлениями кода.
8. С запуском опасных тестов.

---

# 25. Финальное сообщение Codex пользователю

После завершения написать:

```text
Полный аудит после консолидации документации завершён.

Главный вывод:
...

Фактический уровень продукта:
...

Текущий milestone:
...

Можно ли начинать hardening:
...

Главные P0:
...

Главные P1:
...

Полный отчёт:
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md

Черновик будущего ТЗ:
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md

Код не менялся.
БД не менялась.
Тесты не запускались / запускались только safe checks:
...
```

---

# 26. Стартовый промпт для Codex CLI

```text
Проведи полный read-only аудит проекта после консолидации документации по файлу FULL_PROJECT_AUDIT_AFTER_DOCS_TASK.md.

Перед аудитом прочитай:
- AGENT.md
- docs/PROJECT_CONTROL.md
- docs/CURRENT_STATUS.md
- docs/CURRENT_MILESTONE.md
- docs/VERSION_MAP.md
- docs/ROADMAP.md
- docs/SECURITY.md
- docs/METRICS.md
- docs/RECOMMENDATIONS.md
- docs/STEAM_IMPORT.md
- docs/AI_COACH.md
- docs/TESTING.md
- docs/BACKUP_RESTORE.md
- docs/audit/INSTRUCTIONS_VALIDATION_REPORT.md

Важно:
- не меняй код;
- не меняй БД;
- не меняй .env;
- не запускай импорт/Steam/parser jobs;
- не запускай тесты, если test isolation не подтверждён;
- не делай commit;
- новые отчёты пиши на русском языке;
- technical identifiers/commands/files можно оставлять на английском.

Создай:
1. docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md
2. docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md

Отдельно проверь:
- actual product level vs current milestone;
- documentation-to-code alignment;
- security;
- DB/migrations;
- test isolation;
- Steam cursor truth;
- metrics reliability;
- parser facts;
- diagnosis engine;
- recommendation planner;
- AI coach;
- coach-first UI;
- ops/deployment;
- technical debt top-30;
- можно ли начинать hardening.

Начни с read-only preflight.
```

