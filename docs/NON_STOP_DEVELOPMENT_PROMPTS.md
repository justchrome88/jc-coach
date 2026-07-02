# HISTORICAL / PROMPT LIBRARY

This document is retained for context. Do not treat these prompts as active instructions when they conflict with `AGENT.md`, `docs/PROJECT_CONTROL.md` or the user's latest request.

# Non-Stop Development Prompts

Этот файл нужен, чтобы запускать длинные рабочие сессии без потери структуры. Главная цель проекта: построить CS2 coach platform в стиле Scope.gg, но с основным вектором на AI-тренера, который объясняет ошибки, ставит цели и отслеживает прогресс по новым demo.

## Общие правила для каждого большого запуска

Скопируй этот блок в начало любого длинного промта:

```text
Работай автономно и структурно в проекте /opt/jc-coach.
Главный продуктовый вектор: AI CS2 Coach, а не просто витрина статистики.
Статистика нужна как evidence для тренера: ошибки, рекомендации, цели, прогресс.
Не спрашивай подтверждений, если можно сделать разумное решение по коду и документации.
После каждого законченного логического блока:
1. обнови docs;
2. обнови docs/feature_roadmap_scoring_ru.xlsx;
3. прогони ruff и pytest;
4. закоммить;
5. запушь;
6. оставь сервер рабочим на 0.0.0.0:8010.
Коммить часто, маленькими безопасными кусками.
Не коммить runtime файлы из data/uploads, data/incoming_demos, data/reports, data/ai_handoffs.
```

## Prompt 1: DEM Import Production Flow

```text
Сделай следующий блок: DEM Import Production Flow.

Цель: официальный .dem импорт должен быть понятным и надежным для пользователя.

Сделай:
- экран результата импорта DEM;
- parser confidence: high/medium/low;
- event counts: deaths, hurts, round_end, player_team;
- metric confidence для ADR/KAST/entry/utility/score;
- список найденных игроков;
- предупреждения, если score/side/KAST/utility best-effort;
- ссылку на match detail после импорта;
- сохранение parser evidence в raw_json;
- тесты на confidence/evidence/duplicate.

Документация:
- обнови README;
- обнови WORKLOG;
- обнови docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md;
- обнови Excel: Official DEM upload готовность поднять только по факту.

Проверки:
- ruff;
- pytest;
- HTTP smoke для /upload, /matches/{id}, /api/import/demo/inbox если возможно.

Коммит и push.
```

## Prompt 2: Structured Mistake Detection

```text
Сделай следующий блок: Structured Mistake Detection v1.

Цель: перейти от общих weakness-текстов к структурированным ошибкам, которые AI coach сможет объяснять.

Сделай:
- модель/сервис mistake detection без лишней миграционной сложности;
- mistake object: type, title, category, severity, confidence, match_id, metric, threshold, evidence, recommendation;
- правила v1:
  - early_death_problem;
  - bad_entry_duels;
  - low_adr_pressure;
  - low_kast_participation;
  - weak_utility_impact;
  - weak_map;
  - side_imbalance если данных хватает;
- вывод mistakes на /coach;
- вывод per-match mistakes на match detail;
- включение mistakes в AI coach payload;
- тесты на каждое правило и missing data.

Документация и Excel обязательны.
Коммит и push после блока.
```

## Prompt 3: AI Coach Result Persistence

```text
Сделай следующий блок: AI Coach Result Persistence.

Цель: Codex CLI остается текущими мозгами, но результат должен возвращаться в продукт.

Сделай:
- страницу/форму для вставки AI coach ответа из Codex CLI;
- сохранение AI результата как отдельный report type или metadata в coach_reports;
- отображение последнего AI coach report на /coach;
- связку AI report с handoff metadata;
- API endpoint для сохранения AI result;
- валидацию: пустой ответ не сохранять, слишком длинный обрезать/ошибку;
- тесты.

Не подключай OpenAI API.
Provider boundary сохранить: codex_cli_handoff сейчас, local_llm позже.
Документация и Excel обязательны.
Коммит и push.
```

## Prompt 4: Recommendation System 2.0

```text
Сделай следующий блок: Recommendation System 2.0.

Цель: рекомендации должны быть не одной активной целью, а системой тренерских направлений.

Сделай категории рекомендаций:
- aim;
- map;
- crosshair_placement;
- grenades;
- entry_duels;
- survival;
- utility;
- economy позже, если данных хватает.

Сделай:
- несколько активных/архивных рекомендаций;
- status: active, paused, completed, failed, archived;
- baseline/target per category;
- per-match evaluation по каждой активной рекомендации;
- UI на /coach: вкладки/блоки рекомендаций по категориям;
- кнопки complete/pause/archive;
- tests.

Ограничение: не выдумывать metrics, если parser их пока не дает. Для crosshair placement поставить planned/no_data, пока нет координат/углов.
Документация и Excel обязательны.
Коммит и push.
```

## Prompt 5: Super Match Analytics Detail

```text
Сделай следующий блок: Super Match Analytics Detail.

Цель: страница одного матча должна стать главным evidence экраном.

Добавь блоки:
- overview;
- combat;
- ADR profile;
- opening duels;
- survival/KAST;
- utility;
- sides;
- mistakes;
- recommendation evaluations;
- parser confidence.

Если данных нет, показывай disabled/no data state, а не n/a хаос.

Добавь:
- raw evidence summary из raw_json;
- source confidence;
- links назад к /matches и /coach;
- tests/smoke.

Документация и Excel обязательны.
Коммит и push.
```

## Prompt 6: Steam Auth And Match Auto Import Plan/Scaffold

```text
Сделай следующий блок: Steam Auth and Auto Import Scaffold.

Цель: подготовить безопасную основу для будущей автоподгрузки матчей.

Важно:
- Steam login делать через Steam OpenID, не собирать логин/пароль Steam.
- Не хранить Steam пароль.
- Match history/demo flow делать через официальные share/auth-code механизмы, где возможно.

Сделай:
- модели User/SteamAccount/ImportJob или минимальные аналоги;
- Steam OpenID config и routes scaffold;
- UI section "Подключить Steam";
- ImportJob statuses: queued/running/succeeded/failed;
- scheduler scaffold без агрессивного polling;
- документацию по ограничениям Steam/FACEIT;
- tests на модели/status transitions.

Не обещай 100% автоимпорт без проверки реального Steam flow.
Документация и Excel обязательны.
Коммит и push.
```

## Prompt 7: Local LLM Provider Scaffold

```text
Сделай следующий блок: Local LLM Provider Scaffold.

Цель: заменить ручной Codex CLI handoff на локальную LLM, но не ломать текущий codex_cli_handoff.

Сделай:
- LocalLLMProvider для OpenAI-compatible endpoint или Ollama;
- env:
  - AI_PROVIDER=local_llm;
  - LOCAL_LLM_BASE_URL;
  - LOCAL_LLM_MODEL;
- timeout/retry;
- structured JSON response parsing;
- fallback на codex_cli_handoff при ошибке;
- health check endpoint;
- docs как поднять Ollama/LM Studio later;
- tests с mock HTTP server или monkeypatch.

Не требуй реальную local LLM для тестов.
Документация и Excel обязательны.
Коммит и push.
```

## Prompt 8: UI Polish Pass

```text
Сделай следующий блок: UI Polish Pass.

Цель: сделать интерфейс более понятным без превращения в маркетинговый landing.

Сделай:
- аккуратный dashboard layout;
- понятные empty states;
- единые badges/status colors;
- tabs/sections для coach;
- меньше хаоса в таблицах;
- match detail читаемым;
- upload flow понятнее;
- mobile sanity;
- no card-in-card.

Проверить через HTTP smoke и, если возможно, screenshot/визуальную проверку.
Документация и Excel обязательны.
Коммит и push.
```

## Приоритет на день

1. DEM Import Production Flow.
2. Structured Mistake Detection v1.
3. AI Coach Result Persistence.
4. Recommendation System 2.0.
5. Super Match Analytics Detail.
6. Steam Auth and Auto Import Scaffold.
7. Local LLM Provider Scaffold.
8. UI Polish Pass.

Если лимиты подходят к концу, завершить текущий логический блок, прогнать проверки, закоммитить, запушить и оставить подробный статус в `WORKLOG.md`.
