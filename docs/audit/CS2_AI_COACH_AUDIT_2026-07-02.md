# Аудит CS2 AI Coach от 2026-07-02

Задача: аудит текущего проекта без правок кода по `/home/jc/AUDIT_TASK_CS2_AI_COACH.md`.

Ключевой вывод: проект уже перерос простой `v0.1 Personal Dashboard` и имеет реальные зачатки `v0.2 Problem Detection`, `v0.3 Recommendation Engine`, `v0.4 Recommendation Tracking Loop` и `v0.6 AI Coach Summary`. Но фактическое ядро пока ближе к **B/C: problem detector + rule-based recommendation tracking**, а не к полноценному AI coach loop уровня `D`, потому что диагностика и рекомендации в основном rule-based, часть метрик best-effort, а API/security еще не готовы для друзей или public beta.

## Stage 0. Read-only preflight

| Пункт | Результат |
|---|---|
| Путь проекта | `/opt/jc-coach` |
| Пользователь | `root` |
| Ветка | `main` |
| Git status | чистый на момент preflight, незакоммиченных изменений не обнаружено |
| Последний commit | `29ff857 Add swing score metric tracking` |
| Стек | FastAPI, Jinja2, SQLAlchemy, SQLite, pytest, demoparser2, Docker/systemd/nginx |
| Крупные директории | `app/`, `tests/`, `docs/`, `instructions/`, `data/`, `deploy/`, `tools/steam-gc/` |
| README/docs/tests | есть README, много docs/instructions, pytest suite |
| Риск сразу | в рабочем дереве есть `.env` и production-like `data/cs2_coach.db`, поэтому read-only аудит не запускал web endpoints/full pytest |

Тесты не запускались. Причина: `tests/test_web_smoke.py` использует реальный `app`, а `app.main` на lifespan вызывает `init_db()`, который может создавать/апгрейдить реальную SQLite схему. Это противоречит read-only ограничению аудита.

## Addendum 2026-07-02: Steam Auto Import Cursor

После аудита был проверен реальный Steam import flow на подключенном аккаунте.

Факты:

- Steam OpenID подключает только `steam_id`; он не дает приложению права перечислять приватную историю матчей.
- Service bot используется и работает для этапа `share code -> CS2 Game Coordinator -> match_time + demo_url`.
- Service bot не может сам получить список матчей пользователя без пользовательского `Game Authentication Code` и `knowncode` cursor.
- Проверка `GetNextMatchSharingCode` с `knowncode=0` вернула `HTTP 412 Precondition Failed`; значит первый sync не может стартовать только от OpenID + auth code.
- Сохраненный cursor `CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL` был разрешен через Steam GC как матч `2026-05-29T20:45:10`, то есть он старее текущей локальной базы и не ведет к играм 2026-07-02.
- Scope/Leetify-like UX должен оставаться: пользователь один раз вводит два кода со Steam Support, дальше sync автоматический. Нельзя превращать продукт в ручной ввод share code каждого матча.

Вывод:

Steam import нельзя считать production-ready, пока UI и backend явно не диагностируют cursor freshness. Приложение должно показывать дату сохраненного latest share code, предупреждать о старом cursor и не скачивать историю старее последнего импортированного матча.

## Stage 1. Inventory проекта

| Area | Found? | Files/Components | Comment |
|---|---:|---|---|
| Frontend | yes | `app/templates/*.html`, `app/static/app.css`, `app/static/charts.js` | Server-rendered Jinja UI |
| Backend | yes | `app/main.py`, `app/web/routes.py`, `app/api/routes.py` | FastAPI app |
| API routes | yes | `app/api/routes.py` | Много JSON endpoints, но без auth guard |
| Database layer | yes | `app/db/models.py`, `app/db/session.py` | SQLAlchemy models, SQLite create/ALTER |
| Data import | yes | `app/services/importer.py`, `app/services/demo_parser.py`, `app/services/steam_integration.py` | CSV/JSON/DEM/Steam MVP |
| Metrics engine | yes | `app/services/analytics.py`, `app/services/aim_stats.py` | Aggregated metrics + aim profile |
| Diagnosis engine | partial | `app/services/analytics.py::detect_weaknesses`, `app/services/mistake_detection.py` | Rule-based, thresholds mostly hardcoded |
| Recommendation engine | partial | `app/services/recommendation_tracking.py` | Real tables/progress, but recommendations created from fixed categories |
| Tracking loop | yes/partial | `CoachRecommendation`, `MatchRecommendationEvaluation` | Per-match green/yellow/red/gray exists |
| AI/LLM integration | partial | `app/services/ai_coach.py` | Structured payload + Codex handoff + local LLM scaffold |
| Auth/Security | partial | `app/services/auth.py`, middleware in `app/main.py`, nginx basic auth config | Web auth exists; `/api/*` public in app |
| Tests | yes | `tests/*.py` | Good unit coverage, but smoke app tests appear to touch real app/db |
| Docs | yes | README, docs roadmap, feature matrix, strategy, instructions | Strong process docs |
| Deployment | partial | Dockerfile, docker-compose, systemd, nginx | Usable personal deploy, not public hardened |

## Product focus audit

| Пункт | Оценка | Статус | Что найдено | Проблема/риск | Что делать | Приоритет |
|---|---:|---|---|---|---|---|
| Явная цель проекта | 4 | 🟢 | README и `instructions/00_PROJECT_BRIEF.md` формулируют personal coach, docs strategy фиксирует `demo -> parser facts -> analytics -> mistakes -> recommendations -> progress tracking -> AI coach` | Цель есть, но README все еще называет проект `MVP v0.1`, хотя код ушел дальше | Зафиксировать фактическую version map | P1 |
| Roadmap/backlog | 4 | 🟢 | `docs/FEATURE_ROADMAP_SCORING.md`, `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`, `docs/METRICS_ROADMAP_SCORING_RU.md` | Roadmap есть, но часть процентов выглядит оптимистично относительно надежности метрик | Разделить "UI exists" и "metric verified" | P1 |
| MVP scope / LATER | 4 | 🟢 | README явно пишет "Не входит", instructions отделяют Steam/FACEIT/viewer/later | Фактическая разработка уже затронула Steam/AI/provider/recommendations до полной стабилизации parser metrics | Заморозить расширение фич до hardening | P0/P1 |
| Definition of Done | 3 | 🟡 | DoD есть в `NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` | DoD не enforced тестами/CI/релизной версией | Ввести milestone checklist | P1 |
| Ядро продукта | 4 | 🟢 | Coach page показывает focus, mistakes, recommendations, AI handoff | Dashboard все еще первое впечатление статистическое | Сделать active recommendation первым смысловым блоком | P2 |
| Связь метрик с улучшением | 3 | 🟡 | Recommendations оценивают будущие матчи относительно baseline | Часть советов общая, не всегда привязана к точной причине | Recommendation generator от top problems | P1 |

Вывод по рамке:

```text
Проект сейчас больше похож на:
B/C) problem detector + recommendation engine с частичным tracking loop.
Это уже не просто статистический dashboard, но еще не полноценный AI coach loop.
```

Главный вопрос "понимает ли игрок, что делать в следующих 5 матчах?": **частично да**. `/coach` показывает главный фокус, active goals и рекомендации; `/dashboard` показывает "Главная цель тренера". Но качество ответа зависит от weak metrics, а рекомендации создаются по фиксированным категориям, а не всегда от top-1/top-3 verified problems.

## Фактическая версия

| Версия | Фактический статус | Доказательства | Комментарий |
|---|---|---|---|
| v0.1 Personal Dashboard | закрыто | summary, charts, map stats, matches pages | Минимально работает |
| v0.2 Problem Detection | частично | `detect_weaknesses`, `detect_structured_mistakes`, category scorecard | Rule-based, hardcoded thresholds, confidence есть не везде |
| v0.3 Recommendation Engine | частично | `CoachRecommendation`, fixed category definitions | Есть рекомендации, но не полноценная генерация из проблем |
| v0.4 Recommendation Tracking Loop | частично | `MatchRecommendationEvaluation`, green/yellow/red, progress score | Есть loop, но основан на агрегатах и fallback metrics |
| v0.5 Map/Side Deep Dive | начато | map stats, side columns, deep parser tables | Side stats unreliable/None для DEM |
| v0.6 AI Coach Summary | частично | structured payload, prompt, saved AI report | AI не является автономным verified coach; output не структурирован |
| v0.7 Secure Friends Alpha | не готово | web auth есть, `/api/*` публичен | P0 security blocker |
| v0.8 Feedback & Calibration | не обнаружено | feedback usefulness/evals не найдены | Нет пользовательской калибровки |
| v1.0 Public Beta | не готово | нет API auth, migrations, rate limits, privacy hardening | Public beta преждевременна |

Фактическая версия: **v0.4-alpha foundation**, с частичными признаками v0.5/v0.6, но без готовности v0.7.

## Stage 3. Architecture audit

| Layer | Score 0-5 | Status | Evidence | Main Risk | Recommendation |
|---|---:|---|---|---|---|
| Data Layer | 3 | 🟡 | `Match`, deep parser tables, recommendations, users, steam accounts | Нет Alembic; manual SQLite ALTER; multi-user ownership не доведен | Ввести миграции и user scoping |
| Metric Engine | 3 | 🟡 | `analytics.py`, `aim_stats.py`, parser confidence | Формулы частично недокументированы, часть best-effort | Завести `docs/METRICS.md` как source of truth |
| Diagnosis Engine | 2 | 🟡 | `detect_weaknesses`, `mistake_detection.py` | Hardcoded thresholds, no sample-size suppression везде | Rule registry + confidence/min sample |
| Recommendation Engine | 3 | 🟡 | `recommendation_tracking.py` | Fixed default goals создаются автоматически, не от top problem | Problem -> recommendation mapping |
| Tracking Loop | 3 | 🟡 | evaluations, progress score, history | Evaluation side-effect при read calls; weak metrics влияют на goal status | Отделить read от write/evaluate jobs |
| AI Coach Layer | 3 | 🟡 | provider abstraction, handoff files, payload hash | AI output free-form markdown; handoff writes files; no hallucination validator | Structured output schema + post-validation |
| UI/Dashboard | 3 | 🟡 | dashboard, coach, match detail, stats | Много информации; next action не всегда first-screen | Coach-first hierarchy |
| Security/Auth | 1 | 🔴 | `app/main.py` пропускает `/api/`; session secret default | Нельзя безопасно давать доступ друзьям/public | API auth, CSRF, strong secret enforcement |
| Ops/Deployment | 2 | 🟡 | Docker/systemd/nginx basic auth | Docker installs dev deps; no migrations/backup/observability | Production checklist before alpha |
| Docs/Process | 4 | 🟢 | README, roadmap, strategy, worklog | Docs могут опережать фактическую надежность | Add audit/version truth table |

Риск big ball of mud: **средний**. Сервисный слой есть, но некоторые read-функции мутируют БД (`get_active_recommendation_progress()` -> `evaluate_new_matches()` -> commit), а routes напрямую координируют много сервисов.

## Stage 4. Data model audit

| Entity | Status | Evidence | Risk |
|---|---|---|---|
| User/Player | partial | `User`, `SteamAccount`, parser selected player in payload | `Match` не связан с `user_id`; multi-user isolation отсутствует |
| Match | yes | `Match` table | Агрегированная модель перегружена |
| Map | partial | `Match.map_name` | Нет отдельной таблицы/metadata |
| Side T/CT | partial | side columns in `Match`, `DemoPlayerRound.team_side` | DEM side stats low confidence/None |
| Round | yes | `DemoRound` | Есть для parsed DEM |
| Kill/death/event | partial | `DemoDuel`, `DemoDamageEvent` | Нет отдельного raw kill event table, duels approximate |
| Weapon | yes | `DemoWeaponStat` | Accuracy depends on event reliability |
| Utility usage | partial | `DemoGrenadeEvent`, `utility_damage`, `flash_assists` | Attribution best-effort |
| Economy/buy type | no | не обнаружено | Economy coaching невозможен |
| Match metrics | yes | columns in `Match` | Часть fallback |
| Round metrics | partial | `DemoPlayerRound` | Не все round context persisted as metrics |
| Player metrics | partial | `DemoPlayerRound`, `DemoWeaponStat` | No stable player ownership across imports |
| Recommendations | yes | `CoachRecommendation` | Good start |
| Recommendation checks | yes | `MatchRecommendationEvaluation` | Good start |
| Recommendation progress/history | yes | history/status/progress functions | Read side effects |
| AI analysis result | yes | `CoachReport.report_type='ai_coach'`, `report_json` snapshot | Free-form markdown, no schema |
| Import/source metadata | yes | source/external id, `ImportJob`, `DemoParseArtifact` | Good for MVP |

Отдельные вопросы:

| Вопрос | Ответ |
|---|---|
| Можно ли считать first death? | Частично: opening duel/death есть (`entry_deaths`, `DemoPlayerRound.opening_death`), но качество зависит от parser logic |
| Можно ли считать trade kill / traded death? | Trade kill поле есть в `DemoDuel.trade_kill`; traded death/untraded death как метрики не обнаружены |
| Можно ли считать early death до 25 секунд? | Нет надежно: DEM import выставляет `early_deaths = entry_deaths`, warning прямо говорит true timing not implemented |
| Можно ли считать utility impact? | Частично: utility damage/flash assists/enemies flashed есть, но best-effort |
| Можно ли считать map/side split? | Map да; side split не надежно, side stats low confidence |
| Можно ли отслеживать выполнение рекомендаций? | Да, частично: per-match evaluations and progress |
| Хватает ли данных для настоящего тренера? | Недостаточно для зрелого coach: нет economy, reliable side, true early phase, traded deaths, utility impact, position/crosshair |

## Stage 5. Metrics audit

| Metric | Level | Implemented? | Formula documented? | Tested? | Files | Risk |
|---|---|---:|---:|---:|---|---|
| K/D | L1 | yes | partial | yes | `importer.py`, `analytics.py`, `tests/test_analytics.py` | Low |
| ADR | L1 | yes | partial | yes | `demo_parser.py`, `analytics.py`, `aim_stats.py` | Medium for DEM field variance |
| KAST | L1 | partial | no | partial | `demo_parser.py`, `analytics.py` | Best-effort; trade logic incomplete |
| KPR | L1 | no | no | no | не обнаружено | Missing |
| Winrate | L1 | yes | trivial | yes | `analytics.py` | Low |
| HLTV-like rating | L1 | partial | no | no | column only/imported; DEM rating None | Misleading if shown as real rating |
| Impact | L1/L2 | partial | partial | yes | `swing_score`, `WORKLOG`, tests | Custom metric needs docs |
| HS% | L1 | yes | partial | yes | `demo_parser.py`, `aim_stats.py` | Medium |
| Last 15/30 | L1 | yes | yes enough | yes | `compare_periods()` | Low |
| First death rate | L2 | partial | no | partial | `entry_deaths` | Not a true rate |
| Opening duel winrate | L2 | yes/partial | partial | yes | `aim_stats._opening_duel_success` | Depends on entry data |
| Trade kill rate | L2 | partial/no | no | no | `DemoDuel.trade_kill` | Not exposed as rate |
| Traded death rate | L2 | no | no | no | не обнаружено | Critical for KAST/survival |
| Untraded death rate | L2 | no | no | no | не обнаружено | Critical coaching gap |
| Time to kill | L2 | no | no | no | data gap in `aim_stats.py` | Missing |
| Survival time | L2 | no | no | no | no reliable phase timing | Missing |
| Deaths by round phase | L2 | no | no | no | early fallback only | Missing |
| Map split | L2 | yes | trivial | yes/partial | `get_map_stats` | Low/medium |
| Side split | L2 | partial | no | no | side columns, DEM None | High |
| Utility damage | L2 | partial | no | partial | `demo_parser.py`, `analytics.py` | Attribution risk |
| Flash assists | L2 | partial | no | partial | `demo_parser.py` | Field variance |
| Enemies flashed | L2 | partial | no | partial | `demo_parser.py` | Not reliable |
| HE damage | L2 | no specific | no | no | only generic utility damage | Missing |
| Molotov damage | L2 | no specific | no | no | only generic utility damage | Missing |
| Clutch attempts/wins | L2 | columns only/import possible | no | no | `Match.clutches_*` | DEM sets None |
| Eco/force/full-buy | L2 | no | no | no | не обнаружено | Missing |
| "умираешь первым слишком часто" | L3 | partial | partial | yes | `mistake_detection.py`, `recommendation_tracking.py` | Based on entry/early fallback |
| "дерешься без размена" | L3 | partial text | no | no | coach text | No traded death metric |
| "низкий impact при нормальном K/D" | L3 | partial | no | no | `detect_weaknesses` decision_making | Uses KD/winrate only |
| "плохой utility impact" | L3 | partial | no | yes | `mistake_detection.py` | Best-effort utility |
| "плохой CT-side на карте" | L3 | no | no | no | side unreliable | Missing |
| "damage не конвертится в раунды" | L3 | partial | no | no | KD/winrate weakness | Needs round context |
| "плохо выполняешь активную рекомендацию" | L3 | yes/partial | partial | yes | `MatchRecommendationEvaluation` | Good MVP loop |

`METRICS.md`: не обнаружено. Есть `docs/METRICS_ROADMAP_SCORING_RU.md`, но это roadmap/scoring, не definitive formulas/spec.

## Stage 6. Diagnosis engine audit

| Пункт | Оценка | Статус | Что найдено | Проблема | Риск | Что делать | Приоритет |
|---|---:|---|---|---|---|---|---|
| Problem rules | 3 | 🟡 | `detect_weaknesses`, `detect_structured_mistakes` | Rules scattered in analytics/mistake modules | Трудно масштабировать правила | Rule registry | P1 |
| Thresholds | 2 | 🟡 | ADR <70/72, KAST <68/70, utility <45/70, map WR <45 | Hardcoded, не калиброваны | False positives | Document/calibrate thresholds | P1 |
| Last 15 vs previous 15 | 3 | 🟢 | `compare_periods()` | Only aggregate trend | OK for MVP | Keep | P2 |
| Top-3 problems | 2 | 🟡 | mistakes sorted, weaknesses sliced to 6 | No explicit top-3 problem contract | UI/AI may overload | Explicit top-3 with confidence | P1 |
| Ranking | 2 | 🟡 | severity/confidence sort in `mistake_detection.py` | Simple sort, no effect size/sample size | Wrong priority | Add weighted scoring | P1 |
| Map/side | 2 | 🟡 | map yes, side no | side unreliable | Weak map advice incomplete | Side parser hardening | P1 |
| Small sample handling | 1 | 🔴 | Some map min counts, aim confidence | Global rules fire with little data | Self-deception | Min sample + suppress advice | P0/P1 |
| Confidence score | 2 | 🟡 | mistake confidence strings; parser confidence | Not propagated consistently to recommendations | Advice may look too certain | Confidence gating | P1 |
| Explanation | 3 | 🟡 | evidence dicts/text in mistakes | Good MVP start | Needs metric links | Improve evidence UI | P2 |

Есть настоящий начальный problem detector, но он пока rule-based и частично hardcoded. Пользователю можно объяснить часть выводов через evidence, но нельзя считать это зрелой диагностику уровня Scope/Leetify.

## Stage 7. Recommendation engine audit

| Пункт | Оценка | Статус | Что найдено | Проблема | Риск | Что делать | Приоритет |
|---|---:|---|---|---|---|---|---|
| Таблица рекомендаций | 4 | 🟢 | `CoachRecommendation` | Есть | Low | Keep | P3 |
| Active recommendation | 3 | 🟡 | survival active returned for old API | Multi-category goals all active | Focus dilution | One primary + secondary goals | P1 |
| История | 3 | 🟢 | history/list/status/ended_at | Exists | Low | Keep | P2 |
| Статусы | 4 | 🟢 | active/paused/completed/failed/archived | No obsolete | OK | Maybe add obsolete later | P3 |
| Правила создания | 2 | 🟡 | fixed `RECOMMENDATION_DEFINITIONS` | Not generated from detected top problem | Advice can be generic | Map problem->recommendation | P1 |
| Привязка к проблеме | 1 | 🔴 | category only | No explicit `problem_id/type` | Cannot audit why rec exists | Add problem snapshot | P1 |
| Цель/условие выполнения | 3 | 🟡 | baseline/target/success/failure JSON | Formula simple, category-based | Can be misleading if data weak | Confidence-gated target rules | P1 |
| Проверка следующих матчей | 3 | 🟢 | `start_after_match_id`, evaluate non-baseline matches | Good MVP | Read side effects | Move evaluation to explicit job | P1 |
| Progress | 3 | 🟢 | progress_score, counts | Good MVP | Score formula arbitrary | Document formula | P2 |
| Limit active recs | 2 | 🟡 | one per category, not one primary | Four simultaneous goals | Cognitive overload | Primary active recommendation | P1 |
| Why important | 2 | 🟡 | description/comment | Generic | Less trust | Add evidence-backed why | P2 |
| RECOMMENDATIONS.md | partial | 🟡 | `instructions/12_COACH_RECOMMENDATION_TRACKING_TZ.md` | ТЗ есть, runtime spec нет | Docs drift | Runtime spec | P2 |

Честная оценка: **coaching loop есть как MVP-скелет**, не просто текстовые советы. Но это пока не зрелый loop, потому что рекомендации создаются автоматически из фиксированных категорий, а не из verified top problem with confidence.

## Stage 8. AI coach audit

| Пункт | Оценка | Статус | Что найдено | Риск | Что делать | Приоритет |
|---|---:|---|---|---|---|---|
| Structured input | 4 | 🟢 | `build_ai_coach_payload()` includes summary, mistakes, recommendations, recent matches | Good foundation | Keep | P2 |
| Anti-hallucination prompt | 3 | 🟡 | prompt says do not invent, mention gaps | Prompt-only guard | Add output validator | P1 |
| 1-3 actions | 3 | 🟡 | prompt asks concrete focus/actions | Not schema-enforced | Structured JSON output | P1 |
| Check execution | 3 | 🟡 | active/all recommendations in payload | AI not required to bind output to rec id | Add schema fields | P1 |
| Persistence | 4 | 🟢 | `CoachReport` stores report_json snapshot/hash | Strong for MVP | Keep | P2 |
| Separation | 3 | 🟡 | provider layer exists | Payload build calls recommendation functions that write DB | Separate read/write | P1 |
| Provider | 3 | 🟡 | Codex handoff + local_llm scaffold | No production model config confirmed | Manual/local OK | P2 |
| Cost/rate risk | 3 | 🟡 | handoff default avoids web request API calls | local_llm direct endpoint can run on demand | Add rate/auth guard | P1 |

Prompt location: `app/services/ai_coach.py::build_ai_coach_prompt`. Prompt versioning: не обнаружено отдельной версии. Structured output: не обнаружено, AI response сохраняется как markdown. Fallback без AI: есть rule-based reports/recommendations. Hallucination protection: prompt-only, без validator.

## Stage 9. UI/Dashboard audit

| Пункт | Оценка | Статус | Что найдено | Риск | Что делать | Приоритет |
|---|---:|---|---|---|---|---|
| Главная проблема сразу | 3 | 🟡 | `/coach` has "Главный фокус"; dashboard has coach preview | Dashboard first screen begins with stats | Coach-first dashboard option | P2 |
| Active recommendation card | 4 | 🟢 | dashboard and coach show active goal/progress | Good MVP | Keep | P2 |
| Progress by recommendation | 4 | 🟢 | counts/progress score/history | Good MVP | Keep | P2 |
| Last match summary | 3 | 🟡 | recent matches + detail pages | Not "last match coach summary" | Add latest-match coach card | P2 |
| Trend 15/30 | 3 | 🟢 | comparison table/charts | Good MVP | Keep | P3 |
| Map/side breakdown | 2 | 🟡 | map table; side not prominent/reliable | side gap | Do after parser hardening | P1 |
| Metric overload | 2 | 🟡 | many panels on coach page | Can overwhelm | Prioritize next action/top 3 | P2 |
| What to do next | 3 | 🟡 | focus actions and active goal | Sometimes generic | Tie to exact problem/recommendation | P1 |
| Stats vs coach separation | 4 | 🟢 | dashboard/coach separate | Good | Keep | P3 |

## Security/Auth audit

| Пункт | Оценка | Статус | Evidence | Проблема/риск | Что делать | Приоритет |
|---|---:|---|---|---|---|---|
| Web auth | 2 | 🟡 | session auth, register/login, protected web middleware | Basic only, no CSRF/rate limit | Harden before friends | P0 |
| API auth | 0 | 🔴 | `_is_public_path()` returns true for `path.startswith("/api/")` | All API endpoints public at app level | Require auth/API token for non-health APIs | P0 |
| Session secret | 1 | 🔴 | default `change-me-before-public-release` | If `.env` weak/missing, session insecure | Fail startup if default in non-local | P0 |
| Multi-user data isolation | 0 | 🔴 | `Match` has no `user_id`; routes query all matches | Friends would see/mutate same data | Add ownership before friends | P0 |
| CSRF | 0 | 🔴 | forms mutate recommendations/import/settings without CSRF | Cross-site state change risk | CSRF tokens/same-site hardening | P0/P1 |
| Secrets storage | 2 | 🟡 | `.env` gitignored, app setting for steam key | Steam key stored in DB app_settings, UI input | Encrypt/limit/admin-only | P1 |
| Upload safety | 2 | 🟡 | suffix checks for `.dem`, temp files | Large uploads, parse cost DoS | Auth + limits + background queue | P1 |
| Deployment shield | 2 | 🟡 | nginx basic auth config exists | App itself not enough; config may not be deployed | Verify deployed nginx | P0 |

Ответ: **друзьям безопасно давать доступ нельзя**, если только это не закрыто внешней Basic Auth/VPN и все пользователи доверенные. Public beta: **нет**.

## Что уже реально сделано

- Рабочий FastAPI/Jinja MVP с web UI.
- CSV/JSON import с dedupe и tolerant missing columns.
- DEM import через `demoparser2`, parser confidence, event counts, raw payload, deep parser normalized tables.
- Dashboard/matches/stats/coach/match detail pages.
- Core analytics: winrate, KD, ADR, KAST, rating if provided, swing score, last 15 vs previous 15, map stats.
- Initial rule-based weakness/mistake detection.
- Real recommendation tables, lifecycle, per-match evaluations, progress.
- AI handoff payload/prompt, local LLM scaffold, AI report persistence with payload snapshot/hash.
- Steam OpenID/share-code/job scaffolding and service-bot downloader path.
- Unit tests for many services.
- Strong docs/process compared with early MVP.

## Что выглядит готовым, но стоит на слабом фундаменте

| Area | Почему выглядит готовым | Слабый фундамент | Приоритет |
|---|---|---|---|
| Early deaths | Column/UI/recommendations exist | DEM import sets early deaths equal to entry deaths; true timing not implemented | P0/P1 |
| Side/map deep dive | Side columns and map tables exist | Side stats low confidence/None; no reliable side switching | P1 |
| KAST/survival | KAST shown everywhere | Trade/survive/team context is best-effort | P1 |
| Utility impact | Damage/flash metrics shown | Attribution varies by event fields; no lineup/outcome context | P1 |
| AI coach | Payload and reports exist | Output free-form, no validator/schema/calibration | P1 |
| Friends alpha | Auth UI exists | API public, no user scoping | P0 |
| Progress tracking | Green/yellow/red exists | Recommendations not linked to explicit detected problem; evaluation can run during reads | P1 |

## Где есть самообман

1. `v0.1` в README занижает/размывает фактическое состояние: часть v0.4/v0.6 уже сделана, но security для v0.7 не готов.
2. `early_deaths` выглядит как тренерская метрика, но сейчас часто является fallback к `entry_deaths`.
3. `side stats` выглядят предусмотренными, но parser confidence сам помечает side stats как low.
4. `AI coach` звучит сильнее факта: это AI handoff/result persistence, а не автономный validated coach.
5. `Recommendation engine` есть, но рекомендации не являются результатом полноценного diagnosis -> recommendation planner.
6. `Secure friends alpha` не подтвержден, несмотря на login/register.

## Критические технические долги

| Debt | Impact | Priority |
|---|---|---|
| Public `/api/*` without auth | Любой может читать/мутировать данные, импортировать файлы, дергать AI/Steam endpoints | P0 |
| No `user_id` on matches/recommendations/imports | Нельзя безопасно добавить друзей; данные общие | P0 |
| Manual SQLite schema upgrades, no migrations | Риск сломать БД при росте схемы | P0/P1 |
| Read functions mutate DB | Непредсказуемые side effects, read-only тесты/страницы меняют состояние | P1 |
| Early/side/trade metrics unreliable | Coach conclusions могут быть неверными | P1 |
| No formula spec | Нельзя доверять или калибровать метрики | P1 |
| No AI output schema/validation | AI может дать несвязанную рекомендацию | P1 |
| Test app may hit real DB | CI/local tests risk production data | P1 |

## Что нужно заморозить

- Новые конкурентные фичи уровня viewer, heatmaps, clips, training modes.
- Расширение Steam/FACEIT до hardening auth/API/user ownership.
- Новые AI providers до structured output + validator.
- Новые coach categories до стабилизации problem -> recommendation mapping.
- UI-polish, не связанный с next action/progress clarity.

## Что доделать первым

1. **P0 Secure alpha hardening**: закрыть `/api/*`, ввести user scoping, CSRF/rate limits, strong session secret checks.
2. **P1 Metric truth layer**: `docs/METRICS.md`, formula/confidence/source for every displayed metric; suppress weak metrics in diagnosis.
3. **P1 Parser metric hardening**: true early death by timing, side switching, traded/trade death basics.
4. **P1 Recommendation planner**: top problem snapshot -> one primary active recommendation -> measurable target -> future-match checks.
5. **P1 Separate read/write**: evaluation jobs should not run implicitly in GET/read helpers.
6. **P1 Test isolation**: app tests must use temp DB/settings override.

## Friends alpha / public beta decision

| Вопрос | Ответ |
|---|---|
| Можно ли безопасно дать доступ друзьям? | **Нет**, не без внешнего Basic Auth/VPN и доверенной группы. App-level API открыт, multi-user isolation отсутствует. |
| Можно ли думать о public beta? | **Нет**. Нужны API auth, ownership, migrations, privacy, upload/rate hardening, observability, backup. |
| Можно ли продолжать личное использование? | Да, как personal/local/VPS tool с внешней защитой и пониманием metric limitations. |

## Следующий milestone

Рекомендуемый milestone:

```text
v0.7-prep: Secure Single/Friends Alpha + Honest Coach Loop
```

Definition of Done:

1. Все mutating/read-sensitive API закрыты auth.
2. `Match`, recommendations, reports, Steam accounts, jobs имеют user ownership или явно single-user mode.
3. Full test suite изолирован от production DB.
4. `METRICS.md` фиксирует формулы, data source, confidence, suppression rules.
5. Early deaths, side stats, trade/traded death имеют честные статусы: reliable / partial / unavailable.
6. На dashboard/coach есть один primary active recommendation, созданный из top verified problem.
7. GET/read helpers не создают/не оценивают рекомендации неявно.

После этого можно делать закрытый friends alpha для 2-5 человек.

## Итоговые оценки блоков

| Block | Score | Status | Priority |
|---|---:|---|---|
| Product focus | 4 | 🟢 | P1 |
| Version clarity | 2 | 🟡 | P1 |
| Data layer | 3 | 🟡 | P1 |
| Metric engine | 3 | 🟡 | P1 |
| Diagnosis engine | 2 | 🟡 | P1 |
| Recommendation engine | 3 | 🟡 | P1 |
| Tracking loop | 3 | 🟡 | P1 |
| AI coach layer | 3 | 🟡 | P1 |
| UI usefulness | 3 | 🟡 | P2 |
| Security/Auth | 1 | 🔴 | P0 |
| Ops/Deployment | 2 | 🟡 | P1 |
| Docs/Process | 4 | 🟢 | P2 |

Финальный статус: **сильный личный MVP и хороший фундамент под AI coach, но не безопасный friends/public product и не зрелый тренерский loop**.
