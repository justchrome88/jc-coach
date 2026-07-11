# CS2 Personal Coach

> Status: Operator/user entrypoint.
> Current project truth: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md`.
> Human documentation navigation: `docs/README.md` and
> `docs/project_management/DOCS_INDEX.md`.
> The old `v0.1` label describes the original MVP lineage; current factual status is tracked in `docs/CURRENT_STATUS.md`.

Личный FastAPI-инструмент для загрузки матчей CS2 из CSV/JSON/DEM, просмотра аналитики, отслеживания coach-целей и подготовки AI coach handoff.

## Что входит в MVP

- FastAPI приложение с Jinja2 UI.
- SQLite база через SQLAlchemy.
- Импорт CSV/JSON матчей без падения на неполных колонках.
- Прямая загрузка официальных CS2 `.dem` файлов через `demoparser2` с best-effort агрегацией игрока.
- Дедупликация повторно загруженных матчей.
- Dashboard с метриками, графиком Chart.js, качеством данных, ADR-профилем, источниками и формой последних матчей.
- Страница `/matches` с фильтрами по карте, результату, источнику, статусу цели, сортировкой, пагинацией и detail page матча.
- Аналитика summary, сравнение последних 15 против предыдущих 15, статистика по картам.
- Rule-based coach report в Markdown и HTML.
- Coach Recommendation Tracking: active goals по survival, aim, grenades и map, baseline/target и green/yellow/red оценка матчей.
- AI coach handoff для Codex CLI: приложение собирает structured JSON payload и prompt без привязки к OpenAI API.
- AI coach result persistence: сохраненный AI report содержит payload snapshot, provider metadata и payload hash.
- Multi-category recommendation lifecycle: Extend, Restart, Pause, Done, Archive, category summary и history.
- Aim stats profile: ADR/KD/HS/opening duel/multi-kill/weapon breakdown без выдуманных accuracy/spray метрик.
- Steam OpenID + Game Authentication Code onboarding.
- Автоматическая Steam-подгрузка: share-code sync, service bot demo URL resolver, `.dem.bz2` download, parse/import через background job.
- Demo storage lifecycle control: отчет по raw `.dem`, manifest и кандидаты на будущий verified-delete.
- Sample CSV/JSON.
- Pytest-тесты ключевой логики.

Не входит: платежи, demo viewer, React frontend, автоматический запуск локальной LLM, удаление raw `.dem` до утверждения финальных метрик.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Открыть:

- Dashboard: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/health
- Upload: http://127.0.0.1:8000/upload
- Matches: http://127.0.0.1:8000/matches
- Report: http://127.0.0.1:8000/report
- Accounts/imports: http://127.0.0.1:8000/settings/imports
- Demo storage: http://127.0.0.1:8000/settings/storage

## Docker запуск

```bash
docker compose up --build
```

Приложение будет доступно на http://127.0.0.1:8000/.

## Как загрузить sample CSV/JSON/DEM

Через UI:

1. Открыть `/upload`.
2. Выбрать `data/sample_matches.csv`.
3. Нажать `Import`.
4. Открыть `/matches` и `/`.

Через API:

```bash
curl -F "file=@data/sample_matches.csv" http://127.0.0.1:8000/api/import/csv
```

JSON:

```bash
curl -F "file=@data/sample_matches.json" http://127.0.0.1:8000/api/import/json
```

Официальную демку CS2 можно загрузить напрямую:

```bash
curl -F "file=@/path/to/match.dem" \
  -F "player_identifier=your_nickname_or_steamid" \
  http://127.0.0.1:8000/api/import/demo
```

`player_identifier` опционален. Если его не указать, приложение выберет игрока с наибольшей активностью в kill/damage events. Для стабильного личного использования лучше задать `DEMO_PLAYER_IDENTIFIER` в `.env` или указывать поле при загрузке.

Через Bitvise/SFTP на этом сервере можно положить `.dem` в папку:

```text
/home/jc/cs2-demos
```

Это ссылка на inbox приложения:

```text
/opt/jc-coach/data/incoming_demos
```

После загрузки файла откройте `/upload`, блок `Демки из Bitvise`, и нажмите `Импорт` рядом с нужной демкой. API для этого же сценария:

```bash
curl -X POST "http://127.0.0.1:8000/api/import/demo/inbox?filename=match.dem&player_identifier=your_nickname_or_steamid"
```

## Как сгенерировать отчёт

Через UI: открыть `/report` и нажать `Generate new report`.

Через API:

```bash
curl -X POST http://127.0.0.1:8000/api/reports/generate
curl http://127.0.0.1:8000/api/reports/latest
```

Markdown-файлы отчётов сохраняются в `data/reports/`.

## AI Coach: Codex CLI сейчас, local LLM позже

В текущей версии приложение не требует OpenAI API key. AI-слой сделан как заменяемый provider.

Текущий provider:

```text
AI_PROVIDER=codex_cli_handoff
```

Он не вызывает внешнее API из web request. Вместо этого `/coach` по кнопке `Подготовить AI handoff` собирает:

- structured JSON payload с фактами по матчам;
- prompt для Codex CLI;
- metadata с командой запуска.

Файлы сохраняются в:

```text
data/ai_handoffs/
```

API:

```bash
curl http://127.0.0.1:8000/api/coach/ai/payload
curl -X POST http://127.0.0.1:8000/api/coach/ai/handoff
curl http://127.0.0.1:8000/api/coach/ai/handoff/latest
```

Будущий provider:

```text
AI_PROVIDER=local_llm
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=your-model
```

Архитектурно это позволит подключить Ollama/LM Studio/OpenAI-compatible local server без переписывания coach-логики: поменяется только provider, а payload останется тем же.

Текущий scaffold уже поддерживает:

- Ollama-style `POST /api/generate`, если `LOCAL_LLM_BASE_URL` похож на `http://127.0.0.1:11434`;
- OpenAI-compatible `POST /v1/chat/completions` для LM Studio и похожих серверов;
- health endpoint;
- прямую генерацию AI report через provider, когда `AI_PROVIDER=local_llm`.

## Steam import и demo autoload

Steam-интеграция работает через безопасное разделение пользовательского Steam и сервисного bot account:

- пользователь подключает Steam через официальный Steam OpenID;
- пользователь один раз вводит latest match share code `CSGO-...` и Game Authentication Code из Steam Support;
- серверный `STEAM_WEB_API_KEY` лежит в `.env`, пользователю не нужно выпускать свой ключ;
- отдельный service bot обращается к CS2 Game Coordinator по share code и получает replay URL;
- кнопка `/settings/imports` -> “Обновить и скачать демки” ставит `steam_import_all` job;
- web request сразу возвращает страницу, а sync/download/import выполняется в FastAPI background task;
- `.dem.bz2` скачивается с replay host Valve, распаковывается в `.dem` и импортируется через `demoparser2`;
- прогресс доступен в UI и через `GET /api/steam/import/overview`.

Важно:

- Пользовательский Steam пароль, QR, Steam Guard и refresh token не вводятся и не хранятся.
- Service bot не является аккаунтом пользователя и должен быть отдельным пустым аккаунтом без ценного inventory.
- Старые replay URL у Valve могут истекать или временно отдавать HTTP 502/404/410.
- FACEIT пока пропущен в реализации, но остается обязательным будущим источником.

Service bot env:

```text
STEAM_WEB_API_KEY=...
STEAM_BOT_REFRESH_TOKEN=...
```

Альтернативно для первичного входа bot account:

```text
STEAM_BOT_USERNAME=...
STEAM_BOT_PASSWORD=...
STEAM_BOT_SHARED_SECRET=...
```

`STEAM_BOT_TWO_FACTOR_CODE` допускается только для коротких локальных проверок и не должен использоваться как production automation.

Полезные ссылки для настройки:

- Steam Support CS2: `https://help.steampowered.com/en/wizard/HelpWithGame/?appid=730`
- Valve Match History docs: `https://developer.valvesoftware.com/wiki/Counter-Strike%3A_Global_Offensive_Access_Match_History`

Подробная архитектура: `docs/STEAM_IMPORT_ARCHITECTURE.md`.

## Demo storage lifecycle

Целевая схема хранения raw demo:

```text
download -> parse -> verify parsed payload -> delete raw .dem
```

Сейчас raw `.dem` не удаляются: мы еще не утвердили финальный набор метрик и raw-срезов, которые нужно сохранить перед удалением. Вместо удаления внедрен observe-only слой:

- `/settings/storage` показывает объем `data/uploads`, referenced/unreferenced/missing/suspicious файлы, крупные файлы и будущих кандидатов на удаление;
- `GET /api/storage/demos` возвращает тот же отчет JSON;
- `POST /api/storage/demos/manifest` пишет manifest в `data/reports/demo_storage_manifest.json`;
- manifest и raw demo лежат в `data/` и не коммитятся.

Подробное ТЗ: `docs/DEMO_STORAGE_TZ.md`.

## UI language

Интерфейс русскоязычный по умолчанию. Добавлен curated language switch `RU / EN`:

- язык хранится в cookie `locale`;
- текущие ключи переводят навигацию и новые системные страницы;
- это не автоперевод всего текста, а контролируемый словарь в `app/services/i18n.py`, чтобы позднее переводить продукт аккуратно по разделам.

## Общая статистика

Отдельная вкладка `/stats` показывает текущие показатели за выбранный диапазон:

- последние N матчей;
- диапазон дат;
- все матчи.

На странице есть core metrics, динамика, сравнение периодов, качество данных, ADR profile, разбивка по источникам, карты и последние матчи. Dashboard `/dashboard` остается быстрым обзором после входа, а `/stats` становится рабочей аналитической вкладкой.

## Auth and public deployment

Публичный входной экран:

- `/` - landing с кнопками входа и регистрации;
- `/login` - вход;
- `/register` - регистрация;
- `/dashboard` - закрытый dashboard после входа;
- `/logout` - выход.

Session auth использует signed cookie через `SessionMiddleware`; пароль хранится как `pbkdf2_sha256` hash.

На сервере подготовлен production-прокси:

- systemd unit: `/etc/systemd/system/jc-coach.service`;
- nginx site: `/etc/nginx/sites-available/jcnodex`;
- app listens on `127.0.0.1:8010`;
- nginx listens on `80` and proxies domain `jcnodex.ru`.

Репозиторий содержит копии конфигов:

- `deploy/systemd/jc-coach.service`;
- `deploy/nginx/jcnodex.conf`;
- `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`.

## Поддерживаемые CSV поля

Минимально поддерживаются:

```text
played_at,map_name,result,rounds_for,rounds_against,kills,deaths,assists,kd,adr,kast,rating,headshot_percent,entry_kills,entry_deaths,flash_assists,utility_damage,enemies_flashed,clutches_won,clutches_lost
```

Также поддерживаются:

```text
source,external_match_id,demo_file,mode,side_t_rounds_won,side_t_rounds_lost,side_ct_rounds_won,side_ct_rounds_lost
```

Если поля нет или значение пустое, импорт ставит `null`. Если `kd` отсутствует, он считается из `kills / deaths`.

## API

- `GET /health`
- `GET /stats`
- `GET /api/matches`
- `POST /api/import/csv`
- `POST /api/import/json`
- `POST /api/import/demo`
- `GET /api/analytics/summary`
- `GET /api/recommendations/active`
- `GET /api/recommendations`
- `POST /api/reports/generate`
- `GET /api/reports/latest`
- `GET /api/coach/ai/payload`
- `POST /api/coach/ai/handoff`
- `GET /api/coach/ai/handoff/latest`
- `POST /api/coach/ai/result`
- `GET /api/coach/ai/result/latest`
- `GET /api/coach/ai/results`
- `GET /api/coach/ai/provider/health`
- `POST /api/coach/ai/generate`
- `GET /api/analytics/aim`
- `GET /api/recommendations/history`
- `GET /api/recommendations/categories`
- `POST /api/recommendations/{recommendation_id}/extend`
- `POST /api/recommendations/categories/{category}/restart`
- `GET /api/steam/login-url`
- `GET /api/steam/accounts`
- `POST /api/steam/import/share-code`
- `POST /api/steam/import/all`
- `GET /api/steam/import/overview`
- `GET /api/steam/demo-downloader/status`
- `GET /api/storage/demos`
- `POST /api/storage/demos/manifest`
- `GET /api/import/jobs`

## Тесты и линтинг

```bash
pytest
ruff check .
```

## Структура

```text
app/
  api/routes.py
  db/models.py
  db/session.py
  services/importer.py
  services/analytics.py
  services/coach_rules.py
  services/report_generator.py
  services/ai_coach.py
  services/demo_parser.py
  web/routes.py
  templates/
  static/
data/
  sample_matches.csv
  sample_matches.json
tests/
```

## Следующие задачи

- Утвердить полный список метрик/raw-срезов перед включением удаления raw `.dem`.
- Расширить parser payload: rounds, duels, utility, side stats, timing, positions where reliable.
- Добавить verified payload статус и только после этого включать raw demo delete policy.
- Добавить durable worker/scheduler для AI/Steam задач, если FastAPI BackgroundTasks станет недостаточно.
- Довести Steam worker до production scheduler/retry модели.
- Добавить FACEIT sync как второй внешний источник.

Подробные рабочие планы:

- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` - набор промтов для длинных автономных сессий разработки.
- `docs/PRODUCT_EXECUTION_STRATEGY.md` - порядок развития продукта вокруг AI CS2 Coach.
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` - пошаговый план доведения сложных фич до 100%.
