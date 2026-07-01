# CS2 Personal Coach MVP v0.1

Личный FastAPI-инструмент для загрузки матчей CS2 из CSV/JSON, просмотра аналитики и генерации rule-based coach report.

## Что входит в MVP

- FastAPI приложение с Jinja2 UI.
- SQLite база через SQLAlchemy.
- Импорт CSV/JSON матчей без падения на неполных колонках.
- Прямая загрузка официальных CS2 `.dem` файлов через `demoparser2` с best-effort агрегацией игрока.
- Дедупликация повторно загруженных матчей.
- Dashboard с метриками, графиком Chart.js, формой последних матчей и Coach Focus.
- Страница `/matches` с фильтрами по карте, результату и датам.
- Аналитика summary, сравнение последних 15 против предыдущих 15, статистика по картам.
- Rule-based coach report в Markdown и HTML.
- Минимальный Coach Recommendation Tracking: активная цель, baseline, target и green/yellow/red оценка матчей.
- Sample CSV/JSON.
- Pytest-тесты ключевой логики.

Не входит: Steam auth, платежи, публичная регистрация, demo viewer, React frontend.

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

## Как сгенерировать отчёт

Через UI: открыть `/report` и нажать `Generate new report`.

Через API:

```bash
curl -X POST http://127.0.0.1:8000/api/reports/generate
curl http://127.0.0.1:8000/api/reports/latest
```

Markdown-файлы отчётов сохраняются в `data/reports/`.

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
- `GET /api/matches`
- `POST /api/import/csv`
- `POST /api/import/json`
- `POST /api/import/demo`
- `GET /api/analytics/summary`
- `GET /api/recommendations/active`
- `POST /api/reports/generate`
- `GET /api/reports/latest`

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

- Улучшить UI после реального использования.
- Добавить tracking выполнения рекомендаций тренера.
- Расширить импорт под конкретный источник данных.
- Исследовать optional `.dem` parsing через demoparser2 или awpy.
- Позже добавить Steam login только как отдельный этап.
