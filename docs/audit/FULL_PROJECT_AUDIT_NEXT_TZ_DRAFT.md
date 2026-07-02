# Черновик ТЗ: Hardening v0.7-prep после полного аудита

Дата: 2026-07-03.

Это не ТЗ на немедленную реализацию. Это приоритизированный список правок после read-only аудита. Перед началом любой реализации нужно перечитать `AGENT.md`, `docs/PROJECT_CONTROL.md`, `docs/CURRENT_MILESTONE.md`, `docs/SECURITY.md`, `docs/TESTING.md`, `docs/BACKUP_RESTORE.md` и основной аудит `docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md`.

## Цель

Перевести проект из фактического уровня **v0.4-alpha foundation** в контролируемый milestone **v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop** без расширения scope.

## Жёсткие ограничения

- Не добавлять viewer, heatmaps, clips, public profiles, friends/social, FACEIT, payments и training modes до закрытия hardening.
- Не запускать импорт, Steam jobs, parser jobs или общий pytest до подтверждённой test isolation.
- Не менять production DB без проверенного backup/restore.
- Не считать AI coach источником истины: AI только объясняет deterministic facts.
- Не считать наличие login page достаточной безопасностью.

## P0

| Задача | Почему | Acceptance criteria |
|---|---|---|
| Backup/restore stage 0 | Нельзя безопасно менять DB без восстановления | Есть скрипт/процедура backup, restore проверен на копии, docs обновлены |
| Test isolation | `TestClient(app)` может использовать production DB | Safe test command не трогает `data/cs2_coach.db`; есть fail-fast guard |
| Закрыть публичный `/api/*` | Сейчас API считается public path | API требует auth/token, кроме явно public endpoints |
| CSRF для web POST | Session forms без token | Все state-changing web POST защищены |
| Rate limits | Login/import/AI/Steam endpoints открыты для abuse | Есть лимиты на login, upload, AI, Steam/import |
| Strong session secret fail-fast | Дефолтный secret небезопасен | Non-local запуск с дефолтом падает |
| Steam OpenID verification | Callback только парсит claimed_id | Используется Steam `check_authentication`, callback нельзя подделать |
| Запрет dangerous jobs без auth | Steam/import/parser/AI API могут мутировать состояние | State-changing endpoints закрыты и логируются |

## P1

| Задача | Почему | Acceptance criteria |
|---|---|---|
| Single-user mode или ownership | Core tables без `user_id` | Документирован выбор; код enforce-ит выбранную модель |
| DB migration discipline | `create_all` + manual `ALTER` на startup | Есть versioned migrations или замороженный safe migration process |
| Recommendation read/write split | Read helpers делают `commit` | Read methods не создают recommendations/evaluations |
| ProblemSnapshot contract | Planner отсутствует | Есть deterministic problem snapshot с evidence/reliability |
| Primary recommendation planner | Сейчас default categories | Есть одна primary recommendation из top verified problem |
| Metric Truth Layer | Метрики mixed confidence | Есть registry: formula/source/confidence/suppression |
| Parser confidence propagation | Confidence есть, но не управляет diagnosis | Low confidence метрики suppress-ятся |
| Early deaths hardening | Сейчас равны entry deaths | Early death считается по timing/round context или скрывается |
| Trade/traded death hardening | `trade_kill` есть, traded death нет | Trade facts имеют понятные поля и reliability |
| Steam cursor truth | Alpha cursor flow | Нет `knowncode=0` в нормальном пути, UI показывает cursor/freshness статус |
| Steam retry/backoff | Jobs manual/fragile | Durable retries/backoff/status без silent fail |
| AI output validator | Markdown сохраняется без schema | AI результат валидируется по schema или отклоняется |

## P2

| Задача | Почему | Acceptance criteria |
|---|---|---|
| Coach-first UI pass | Dashboard stats-first | Первым экраном является next action/primary problem |
| Upload size/stream guard | App читает файл целиком | Есть app-level limit и user-facing error |
| Observability | Нет structured app logs/monitoring | Ошибки jobs/import/AI видны оператору |
| Raw demo retention policy | `.dem` сохраняются | Есть понятная политика хранения/удаления |
| Deployment rollback | Нет rollback plan | Есть documented rollback для app + DB |

## P3

| Задача | Условие |
|---|---|
| Viewer | Только после hardening и parser truth |
| Heatmaps | Только после movement/position facts |
| Clips | Только после demo storage/privacy policy |
| Public profiles | Только после ownership/security |
| Friends/social | Только после friends alpha gate |
| FACEIT | Только после стабильного core loop |

## Suggested Implementation Order

1. Freeze current runtime state and document no-jobs/no-tests constraints.
2. Backup `data/cs2_coach.db` and runtime artifacts.
3. Verify restore on a copy.
4. Add test isolation and safe test command.
5. Add security fail-fast checks.
6. Protect API and state-changing web routes.
7. Add CSRF and rate limits.
8. Decide and implement single-user mode or ownership.
9. Move schema changes to controlled migration process.
10. Split recommendation reads from writes.
11. Add `ProblemSnapshot` and primary recommendation planner.
12. Add Metric Truth Layer and confidence suppression.
13. Harden parser-derived metrics.
14. Harden Steam cursor/retry/freshness.
15. Add AI output schema/validator.
16. Run coach-first UI pass after truth layers are stable.

## Milestone 1 DoD: Safety Foundation

- Backup/restore documented and manually verified.
- Safe test command exists and cannot touch production DB.
- General pytest does not mutate `data/cs2_coach.db`.
- API exposure inventory is complete.
- Default secret fail-fast exists for non-local run.
- No imports/Steam/parser jobs are required for validation.

## Milestone 2 DoD: Secure Single Alpha

- Public `/api/*` removed or protected.
- State-changing routes require auth and CSRF/rate protection.
- Single-user/ownership model enforced.
- Steam OpenID callback verifies Steam assertion.
- Upload size guard exists.
- Security docs and release checklist updated.

## Milestone 3 DoD: Honest Coach Loop

- Metric registry exists with source/formula/confidence/reliability.
- Low-confidence metrics are suppressed from diagnosis/recommendations.
- Recommendation reads are read-only.
- `ProblemSnapshot` links diagnosis evidence to primary recommendation.
- One primary recommendation is selected deterministically.
- AI output is schema-validated and bound to payload/problem/recommendation.

## Safe Verification Plan

- До test isolation: только static/read-only checks (`git status`, `rg`, `sed`, `nl`, `python -m compileall` только после отдельного согласования, если не импортирует app startup).
- После test isolation: safe unit tests against in-memory or temp DB.
- После backup/restore: migration dry-run on copied DB.
- После API auth: smoke checks against temp DB and authenticated test session.

## Next Prompt для Codex

```text
Начни hardening stage 0: backup/restore + test isolation.

Перед работой прочитай AGENT.md, docs/PROJECT_CONTROL.md, docs/CURRENT_MILESTONE.md,
docs/SECURITY.md, docs/TESTING.md, docs/BACKUP_RESTORE.md,
docs/audit/FULL_PROJECT_AUDIT_AFTER_DOCS.md и
docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md.

Не запускай импорт, Steam jobs, parser jobs и общий pytest до подтверждения test isolation.
Не меняй production DB без backup.
Сначала покажи план безопасных изменений, затем реализуй только stage 0.
```
