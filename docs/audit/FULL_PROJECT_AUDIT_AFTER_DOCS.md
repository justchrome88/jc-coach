# Полный аудит проекта после консолидации документации

Дата аудита: 2026-07-03.

## 1. Verdict

**PASS_WITH_WARNINGS** для документационной консолидации.

Документация теперь описывает проект как управляемую систему с главным source of truth в `docs/PROJECT_CONTROL.md`. Код при этом подтверждает, что продукт ещё не готов для friends/public режима: hardening можно начинать только с этапа test isolation и backup/restore, без импорта, Steam jobs, parser jobs и небезопасного pytest.

## 2. Executive Summary

- Фактический уровень продукта: **v0.4-alpha foundation**.
- Текущий milestone разработки: **v0.7-prep — Secure Single/Friends Alpha + Honest Coach Loop**.
- Канонические документы в целом честно отражают состояние кода: security, metrics, recommendations, Steam и AI описаны как неполные/alpha, а не как production-ready.
- Главные P0: публичный `/api/*`, отсутствие ownership у core-данных, отсутствие CSRF/rate limits, дефолтный `SESSION_SECRET_KEY`, неподтверждённый Steam OpenID callback, небезопасная test isolation, отсутствие backup/restore scripts.
- Главные P1: отсутствие metric truth layer, planner problem snapshot, read-only границ в recommendation service, миграций, parser confidence propagation и validator для AI coach.
- Итог по запуску hardening: **да, но только с test isolation + backup/restore как первого этапа**.

## 3. Actual Product Level vs Current Milestone

| Область | Реальный уровень | Требование milestone | Вывод |
|---|---|---|---|
| Product level | `v0.4-alpha foundation` | Не путать с milestone | Совпадает с canonical docs |
| Milestone | `v0.7-prep` | Secure Single/Friends Alpha + Honest Coach Loop | Это цель hardening, не текущая готовность |
| Friends/public | Не готово | Закрыть security P0 | Нельзя открывать наружу без внешнего proxy/basic auth/VPN |
| Coach loop | Есть lifecycle и отчёты | Verified problem -> primary recommendation -> validated AI | Частично, planner отсутствует |
| Steam import | Alpha flow | Cursor truth + retry + ownership | Частично |
| Metrics | Mixed confidence | Runtime metric truth layer | Не готово |

## 4. Preflight

| Проверка | Результат |
|---|---|
| Working directory | `/opt/jc-coach` |
| Пользователь | `root` |
| Git branch | `main` |
| Git status | Рабочее дерево уже было dirty: много docs/instructions modified и untracked canonical/audit files |
| Последние коммиты | Последние изменения касались Steam freshness, swing score, roadmap scoring, parser persistence, AI recommendations |
| Runtime data | `.env`, `data/*.db`, `data/reports/*` не трогались |
| Тесты/jobs | Не запускались |
| Read-only граница | Для аудита запускались только `git`, `find`, `sed`, `nl`, `rg`; создано только два audit-документа |

## 5. Documentation-to-code Alignment

| Документ | Alignment | Evidence | Риск |
|---|---|---|---|
| `docs/PROJECT_CONTROL.md` | Хорошо | Версия и frozen scope совпадают с кодовыми рисками | Низкий |
| `docs/CURRENT_STATUS.md` | Хорошо | `v0.4-alpha foundation` соответствует реальной зрелости | Низкий |
| `docs/CURRENT_MILESTONE.md` | Хорошо | Hardening-first порядок нужен по фактам безопасности | Низкий |
| `docs/SECURITY.md` | Хорошо | Код подтверждает P0: публичный `/api/*`, нет CSRF/rate limits/ownership | Низкий |
| `docs/METRICS.md` | Частично | Документ честно слабый; runtime registry нет | Средний |
| `docs/RECOMMENDATIONS.md` | Хорошо | Lifecycle есть, planner/problem snapshot отсутствует | Средний |
| `docs/STEAM_IMPORT.md` | Хорошо | Steam alpha, cursor truth частично есть, production hardening нет | Средний |
| `docs/AI_COACH.md` | Хорошо | AI handoff/persistence есть, validator/schema нет | Средний |
| `docs/TESTING.md` | Хорошо | Код подтверждает риск production DB при `TestClient(app)` | Высокий до isolation |
| `docs/BACKUP_RESTORE.md` | Хорошо как gap-doc | Backup scripts не найдены | Высокий до hardening |

## 6. Architecture Scorecard

| Layer | Score | Комментарий |
|---|---:|---|
| Import/data ingestion | 3/5 | CSV/JSON/DEM/Steam есть, но небезопасные API и jobs |
| Parser facts | 3/5 | Deep tables есть, confidence есть, часть фактов best-effort |
| Metrics engine | 2/5 | Агрегации есть, registry/formula contract/suppression нет |
| Metric Truth Layer | 1/5 | Практически отсутствует как runtime слой |
| Diagnosis engine | 2/5 | Правила есть, но без центрального reliability gate |
| Recommendation lifecycle | 3/5 | Baseline/target/evaluations/history есть |
| Recommendation planner | 1/5 | Нет `ProblemSnapshot`, top verified problem и read-only границ |
| AI coach | 2/5 | Handoff/persistence есть, output validation нет |
| Web UI | 3/5 | UI рабочий, но coach-first не доминирует |
| API | 1/5 | Функционально широкое, но публичное |
| Auth/security | 1/5 | Login есть, но нет API auth, CSRF, ownership, rate limit |
| DB/migrations | 1/5 | SQLite + startup `create_all`/manual `ALTER`, Alembic нет |
| Testing | 2/5 | Unit fixtures есть, suite isolation не доказана |
| Ops/deploy | 2/5 | Docker/systemd/nginx есть, backup/monitoring/rollback слабые |
| Docs/process | 4/5 | После консолидации управление стало понятным |

## 7. Security Audit

### P0 findings

| Finding | Evidence | Impact |
|---|---|---|
| Весь `/api/*` публичный | `app/main.py:_is_public_path()` включает `path.startswith("/api/")` | Любой может читать/писать API при внешней публикации |
| API endpoints мутируют данные без auth | `app/api/routes.py` содержит import, report, AI, Steam, storage POST endpoints | Риск удаления/порчи состояния, запуска heavy jobs |
| Нет ownership на core-таблицах | `Match`, `CoachReport`, `CoachRecommendation`, `MatchRecommendationEvaluation`, `ImportJob` без `user_id` | Multi-user/friends невозможен безопасно |
| CSRF не обнаружен | Web forms используют POST без token | Session-auth POST уязвим при внешней публикации |
| Rate limits не обнаружены | Нет middleware/dependency для login/API/import/AI/Steam | Brute force и abuse |
| Дефолтный secret | `app/config.py` задаёт `session_secret_key = "change-me-before-public-release"` | Нельзя запускать публично без fail-fast |
| Steam OpenID callback не проверяет assertion | `validate_openid_callback()` только извлекает `openid.claimed_id` | Возможна подмена callback при внешней публикации |
| Upload reads full file | Upload/import endpoints читают файл целиком; nginx limit не является app-level guard | Memory/DoS риск |

### Security verdict

| Режим | Вердикт |
|---|---|
| Local personal | Допустимо |
| Personal VPS за VPN/basic auth | Условно допустимо |
| Friends alpha | Нет |
| Public beta | Нет |

## 8. Database and Migration Audit

- Основная БД по умолчанию: `sqlite:///.../data/cs2_coach.db`.
- `app/db/session.py` создаёт global `engine` при импорте.
- Startup вызывает `Base.metadata.create_all(bind=engine)` и `_upgrade_sqlite_schema()`.
- `_upgrade_sqlite_schema()` делает ручные `ALTER TABLE` для `matches`, `coach_reports`, `users`, `coach_recommendations`.
- Alembic или другой versioned migration layer не найден.
- Backup/restore scripts не найдены.
- `.env` и `data/*.db` игнорируются git, но runtime DB существует локально.

Вывод: до любых schema/security изменений нужен backup/restore этап и миграционный план.

## 9. Test Isolation Audit

| Проверка | Результат |
|---|---|
| Unit fixture | `tests/conftest.py` создаёт in-memory SQLite для `db` fixture |
| Web smoke tests | `tests/test_web_smoke.py` импортирует `app.main:app` |
| App startup | `app.main` lifespan вызывает `init_db()` |
| DB engine | `app.db.session` создаёт global engine на `DATABASE_URL` из `.env`/defaults |
| Итог | Полный pytest небезопасен до доказанной изоляции |

Тесты в рамках аудита не запускались. Следующий безопасный шаг: отдельный test environment, override `DATABASE_URL`, override `SessionLocal/engine`, запрет доступа к `data/cs2_coach.db` в тестах.

## 10. Steam Import Audit

| Область | Статус | Evidence | Gap |
|---|---|---|---|
| Steam OpenID login URL | Есть | `steam_login_url()` | Callback assertion не валидируется |
| Account linking | Есть | `link_steam_account()` | При `user_id=None` создаёт нового user, ownership неясен |
| Game Authentication Code | Есть | `update_match_auth_code()` | Нет user scoping |
| Latest share code cursor | Есть частично | Требуется `last_share_code`; `known_code = payload or account.last_share_code or "0"` | Остаточный путь `knowncode=0` |
| Match-history sync | Есть | `_collect_match_share_codes()` и `GetNextMatchSharingCode` | Нет durable scheduler/retry/backoff/rate limit |
| Pull all | Есть | `run_steam_import_all_job()` | Запуск через public API опасен |
| Freshness truth | Частично | Skip старше latest imported через `min_played_at` | UI/diagnostics ещё не достаточно hard |
| Demo downloader | Alpha | Node Steam GC helper | Требует отдельного operational hardening |

Steam import readiness: **alpha**, не production-ready.

## 11. Metrics Audit

| Метрика | Есть в коде | Reliability | Основной риск |
|---|---|---|---|
| Winrate | Да | High при валидном result | Нет source confidence |
| K/D | Да | High из kill/death events или upload | Нет runtime formula registry |
| ADR | Да | Medium/High, parser ставит confidence | Не везде suppress при low confidence |
| KAST | Да | Medium/Low | Best-effort, не строгая demo truth |
| Rating | Да | Mixed | Для demo часто `None` |
| Swing score | Да | Medium | Formula не закреплена в metric contract |
| Entry kills/deaths | Да | Medium | Зависит от parser approximation |
| Early deaths | Да | Low | В parser сейчас `early_deaths = entry_deaths` |
| Utility damage | Да | Medium | Зависит от damage event coverage |
| Flash assists/enemies flashed | Да | Medium/Low | Parser/event completeness |
| Side splits | Поля есть | Low | Parser confidence фиксирует `side_stats = low` |
| Trade kill | Deep table есть | Low/Medium | Есть `trade_kill`, нет traded/untraded death |
| Clutch/economy | Поля/категории частично | Low/No data | Не реализовано надёжно |
| Crosshair placement | Нет | No data | Mistake engine честно помечает data gap |

Вывод: метрики можно показывать как alpha analytics, но нельзя использовать как hard coach truth без `Metric Truth Layer`.

## 12. Parser Facts Audit

Что уже есть:

- `demoparser2` integration.
- Header, player info, deaths, damage, round events, teams, weapon fire, blinds, grenades, bomb events.
- Deep tables: `DemoParseArtifact`, `DemoRound`, `DemoPlayerRound`, `DemoWeaponStat`, `DemoDamageEvent`, `DemoDuel`, `DemoGrenadeEvent`.
- `parser_confidence`, `metric_confidence`, warnings, event counts, payload version.

Критичные ограничения:

- `early_deaths` сейчас равны `entry_deaths`.
- `side_stats` всегда low confidence.
- `trade_kill` есть, но `traded_death`/`untraded_death` нет.
- Нет full movement/view-angle timeline для crosshair placement.
- Parser import вызывает `ensure_default_recommendation()` и `evaluate_new_matches()`, то есть импорт demo имеет recommendation side effects.
- Raw `.dem` сохраняются; deletion policy не включён.

Parser verdict: **хорошая foundation, но не hard truth layer**.

## 13. Diagnosis Engine Audit

| Область | Статус | Gap |
|---|---|---|
| Weakness detection | Есть hardcoded thresholds в `analytics.detect_weaknesses()` | Нет confidence gate |
| Structured mistakes | Есть `mistake_detection.detect_structured_mistakes()` | Нет central problem registry |
| Category scorecard | Есть | Нет verified top problem contract |
| Crosshair placement | Честно `no_data` | Нужны parser facts до выводов |
| Map problems | Есть | Sample guard слабый/разный в разных местах |
| Decision making | Есть generic signal | Нет доказательной связи с round facts |

Вывод: diagnosis engine годится для подсказок, но не для автономного выбора главной тренерской задачи без planner layer.

## 14. Recommendation Planner and Tracking Audit

Что реализовано:

- `CoachRecommendation`, `MatchRecommendationEvaluation`.
- Baseline/target periods.
- Success/failure rules.
- Status lifecycle: active/paused/completed/failed/archived.
- History and category summary.

Главные проблемы:

- Нет `ProblemSnapshot`.
- Нет связи recommendation -> verified problem/evidence snapshot.
- `ensure_default_recommendations()` создаёт несколько активных системных рекомендаций по категориям.
- `get_active_recommendation_progress()`, `get_all_recommendation_progress()`, `get_evaluations_by_match_id()`, `get_all_evaluations_by_match_id()`, `list_recommendation_history()` могут создавать рекомендации или оценки через `commit`.
- `get_active_recommendation_progress()` выбирает survival/default, а не top verified problem.

Вердикт: lifecycle есть, planner отсутствует. Перед honest coach loop нужно разделить read/write и построить explicit planner.

## 15. AI Coach Audit

| Область | Статус | Gap |
|---|---|---|
| Structured input payload | Есть | Payload может иметь side effects через recommendation progress |
| Handoff provider | Есть `codex_cli_handoff` | Не является autonomous coach |
| Local LLM provider | Есть | Нет auth/rate limit для public API endpoint |
| Report persistence | Есть `CoachReport` metadata/hash/snapshot | Нет output schema и validator |
| Prompt rules | Есть | Prompt rules не заменяют validation |
| Binding to recommendation/problem | Частично через payload | Нет stable problem_id/recommendation_id contract |

AI maturity: **handoff/freeform_summary**, не `validated_coach`.

## 16. UI/UX Coach-first Audit

Итоговый тип UI: **hybrid / partially coach-first**.

| Проверка | Результат |
|---|---|
| Что делать в следующих 5 матчах видно сразу | Частично, сильнее на `/coach`, слабее на dashboard |
| Primary recommendation card | Есть элементы recommendation progress, но нет verified primary problem |
| Why this problem | Частично через evidence/weaknesses |
| Target/progress | Есть в recommendation lifecycle |
| Last match coach summary | Частично через match detail/report |
| Top-3 problems | Есть structured mistakes/weaknesses |
| Reliability/suppression labels | Частично, неполно |
| Raw stats ниже coach action | Не всегда; dashboard stats-first |
| Steam import state | Есть, но alpha/freshness UX нужно усилить |
| AI coach state | Есть handoff/provider health/history |

Вывод: UI уже полезен, но не должен диктовать product truth. Нужна перестановка в сторону primary action после planner/metric truth.

## 17. Ops/Deployment Audit

| Область | Статус | Gap |
|---|---|---|
| Dockerfile | Есть | Копирует `data` в image, env separation слабая |
| docker-compose | Есть | Использует `.env.example`, bind-mount `./data` |
| systemd | Есть | Локальный uvicorn на `127.0.0.1:8010` |
| nginx | Есть | Basic auth и `client_max_body_size 2048m` |
| HTTPS | Не видно | Конфиг слушает HTTP |
| Healthcheck | `/health` есть | Нет полноценного deploy health policy |
| Logs | nginx logs, systemd stdout | Нет structured app logging |
| Backup | Документирован как gap | Scripts не найдены |
| Restore | Документирован как gap | Проверенного процесса нет |
| Rollback | Не обнаружен | Нет release artifact/versioning |
| Monitoring | Не обнаружен | Нет observability |

Deployment readiness: **personal_vps only behind external protection**, не friends/public.

## 18. Technical Debt Top-30

| # | Debt | Evidence | Impact | Severity | Priority | Recommended fix |
|---:|---|---|---|---|---|---|
| 1 | Публичный `/api/*` | `app/main.py:_is_public_path` | Полный внешний доступ к API | Critical | P0 | Закрыть API auth/session/token |
| 2 | Нет ownership core data | `Match` и coach tables без `user_id` | Friends невозможен безопасно | Critical | P0 | Single-user mode или user scoping |
| 3 | Нет CSRF | Web POST forms без token | Session attack риск | High | P0 | CSRF middleware/tokens |
| 4 | Нет rate limits | Login/import/AI/Steam без limits | Abuse/DoS/bruteforce | High | P0 | Rate limiting layer |
| 5 | Default session secret | `SESSION_SECRET_KEY=change-me...` | Session compromise | High | P0 | Fail-fast in non-local |
| 6 | Steam OpenID assertion не проверяется | `validate_openid_callback()` | Account spoof risk | Critical | P0 | Verify `check_authentication` |
| 7 | Test suite может тронуть production DB | `TestClient(app)` + global engine | Data corruption | Critical | P0 | Isolated test settings |
| 8 | Нет backup/restore scripts | Только docs placeholder | Нельзя безопасно менять DB | Critical | P0 | Backup/restore automation |
| 9 | Нет migrations | `create_all` + manual `ALTER` | Schema drift/data loss | High | P1 | Alembic/versioned migrations |
| 10 | Startup mutates schema | `init_db()` | Непредсказуемый deploy | High | P1 | Remove runtime schema upgrades |
| 11 | Recommendation reads mutate DB | `get_*progress()` вызывает commit path | Нельзя безопасно читать | High | P1 | Split read/write services |
| 12 | Нет ProblemSnapshot | Models/service | Нет honest planner | High | P1 | Add problem snapshot contract |
| 13 | Multiple default active recs | `RECOMMENDATION_DEFINITIONS` | Нет primary focus | Medium | P1 | Planner selects one primary |
| 14 | Нет metric registry | `analytics.KEY_METRICS` only | Формулы неуправляемы | High | P1 | Runtime metric truth registry |
| 15 | Нет suppression by reliability | analytics/diagnosis | Low confidence drives advice | High | P1 | Reliability gates |
| 16 | `early_deaths = entry_deaths` | `demo_parser.py` | Misleading survival metric | Medium | P1 | Timing-based early death |
| 17 | Нет traded/untraded death | `DemoDuel` only `trade_kill` | Trade diagnosis weak | Medium | P1 | Add/parser facts |
| 18 | Side stats low | parser confidence | Map-side advice unreliable | Medium | P1 | Side/team truth hardening |
| 19 | Steam scheduler weak | Background/manual jobs | Unreliable sync | Medium | P1 | Durable worker/retry/backoff |
| 20 | Steam job ownership weak | `ImportJob` lacks user_id | Cross-user leakage risk | High | P1 | Scope jobs |
| 21 | Residual `knowncode=0` | `sync_match_history_job()` | Freshness/412 risk | Medium | P1 | Require validated cursor |
| 22 | Steam API key can live in DB | `AppSetting` usage | Secret management weak | Medium | P1 | Env/secret storage policy |
| 23 | Upload reads full files | API/web import handlers | Memory/DoS | High | P1 | App-level size/stream guard |
| 24 | AI output unvalidated | `save_ai_coach_result()` markdown only | Hallucinated coach advice | High | P1 | JSON schema + validator |
| 25 | AI endpoints public via API | `/api/coach/ai/*` | Abuse/cost/data exposure | High | P0 | Protect API |
| 26 | Parser import triggers rec eval | `import_demo_file()` | Import has hidden side effects | Medium | P1 | Explicit post-import evaluator |
| 27 | Raw demo retention unmanaged | demo storage policy | Privacy/storage risk | Medium | P2 | Retention policy + operator confirmation |
| 28 | No observability | Ops files | Hard incidents | Medium | P2 | Structured logs/metrics |
| 29 | Coach UI not primary enough | Dashboard stats-first | Product loop weaker | Medium | P2 | Coach-first redesign after planner |
| 30 | Dirty/untracked docs process | `git status` preflight | Process ambiguity | Low | P2 | Owner review and commit strategy |

## 19. Roadmap Correction

1. Hardening можно начинать, но первым этапом должен быть **test isolation + backup/restore**.
2. Security P0 должен идти до friends/public, Steam automation и AI generation hardening.
3. Преждевременны: viewer, heatmaps, clips, public profiles, friends/social, FACEIT, training modes, payments.
4. В `LATER.md` должны оставаться расширения, которые не закрывают current milestone.
5. После аудита стали актуальнее: OpenID verification, API auth, CSRF, metric registry, recommendation read/write split.
6. 7 дней: test isolation, backup/restore, API exposure inventory, secret fail-fast plan.
7. 14 дней: security P0 closure, single-user/ownership decision, safe CI.
8. 30 дней: metric truth layer, planner snapshot, Steam cursor truth, AI schema validator.

## 20. Must Fix Before Hardening

Перед любыми содержательными hardening-изменениями:

1. Создать проверенный backup/restore процесс для `data/cs2_coach.db` и runtime артефактов.
2. Изолировать тесты от production DB.
3. Зафиксировать safe test command.

Перед friends alpha:

1. Закрыть public `/api/*`.
2. Ввести CSRF/rate limits.
3. Ввести strong secret fail-fast.
4. Решить single-user vs ownership.
5. Проверить Steam OpenID callback.

## 21. Can Hardening Start?

**Да, но только как controlled hardening stage 0: test isolation + backup/restore.**

Нельзя начинать с viewer/heatmaps/clips/public/friends. Нельзя запускать импорт, Steam jobs, parser jobs или общий pytest до подтверждённой изоляции.

## 22. Draft Next Fix TZ Summary

Черновик следующего ТЗ создан в `docs/audit/FULL_PROJECT_AUDIT_NEXT_TZ_DRAFT.md`. Он предлагает порядок:

1. Backup/restore.
2. Test isolation.
3. Security P0.
4. Ownership/single-user mode.
5. Migration discipline.
6. Recommendation read/write split.
7. Metric Truth Layer.
8. Parser hardening.
9. Steam cursor truth.
10. AI validator.
11. Coach-first UI.

## 23. Final Verdict

Документационная система после консолидации стала достаточно цельной, чтобы управлять проектом. Она не скрывает фактическое состояние продукта и правильно блокирует расширение scope до hardening.

Главный технический вывод: кодовая база функционально богаче, чем `v0.1`, но по безопасности, тестовой изоляции и truth layer всё ещё находится на уровне **v0.4-alpha foundation**. Текущий milestone **v0.7-prep** достижим, если первым этапом закрыть безопасность данных и воспроизводимость проверок.
