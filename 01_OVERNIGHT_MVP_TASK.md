# ТЗ для ночной задачи Codex: CS2 Personal Coach MVP v0.1

## Контекст

Нужно за один длинный прогон Codex сделать первый рабочий MVP личного CS2-тренера.

Главная цель ночного прогона: не построить полный продукт, а получить рабочую базу, куда можно загрузить данные матчей и увидеть аналитику + тренерский отчёт.

Работать автономно, но не раздувать scope. Если возникает выбор между красивой архитектурой и работающим результатом — выбирать работающий результат, но без откровенного мусора в коде.

## Цель MVP v0.1

Создать веб-приложение, которое:

1. Поднимается на Ubuntu VPS.
2. Позволяет загрузить CSV/JSON с матчами CS2.
3. Сохраняет матчи в БД.
4. Показывает дашборд по последним матчам.
5. Сравнивает последние N матчей с предыдущими N.
6. Показывает аналитику по картам.
7. Находит слабые места rule-based алгоритмом.
8. Генерирует coach report в Markdown/HTML.
9. Имеет понятную структуру проекта и README.

## Не делать в ночной задаче

Не делать:
- Steam OAuth/OpenID;
- автоматическую загрузку матчей из Steam;
- полноценный demo viewer;
- платежи;
- регистрацию пользователей;
- красивый маркетинговый лендинг;
- сложный React frontend;
- Docker Swarm/Kubernetes;
- микросервисы;
- многопользовательские кабинеты.

Если успеешь базовый MVP, можно добавить поддержку загрузки .dem как experimental, но только после завершения CSV/JSON импорта и отчёта.

## Стек

Использовать:

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite по умолчанию для простоты
- возможность позже заменить на PostgreSQL
- Jinja2 templates
- Chart.js
- python-multipart для загрузки файлов
- pandas опционально для CSV-импорта
- pydantic-settings
- pytest
- ruff

## Структура проекта

Создать структуру:

```text
cs2-coach/
  app/
    __init__.py
    main.py
    config.py

    db/
      __init__.py
      session.py
      models.py

    services/
      importer.py
      analytics.py
      coach_rules.py
      report_generator.py
      demo_parser.py

    api/
      __init__.py
      routes.py

    web/
      __init__.py
      routes.py

    templates/
      base.html
      dashboard.html
      upload.html
      matches.html
      report.html

    static/
      app.css
      charts.js

  data/
    uploads/
    reports/
    sample_matches.csv
    sample_matches.json

  tests/
    test_importer.py
    test_analytics.py
    test_coach_rules.py

  README.md
  pyproject.toml
  .env.example
  Dockerfile
  docker-compose.yml
```

## Модель данных MVP

### Таблица `matches`

Поля:

- `id`
- `source`
- `external_match_id`
- `demo_file`
- `played_at`
- `map_name`
- `mode`
- `result`
- `rounds_for`
- `rounds_against`
- `kills`
- `deaths`
- `assists`
- `kd`
- `adr`
- `kast`
- `rating`
- `headshot_percent`
- `entry_kills`
- `entry_deaths`
- `flash_assists`
- `utility_damage`
- `enemies_flashed`
- `clutches_won`
- `clutches_lost`
- `side_t_rounds_won`
- `side_t_rounds_lost`
- `side_ct_rounds_won`
- `side_ct_rounds_lost`
- `raw_json`
- `created_at`
- `updated_at`

### Таблица `coach_reports`

Поля:

- `id`
- `period_start`
- `period_end`
- `matches_count`
- `report_markdown`
- `report_json`
- `created_at`

## Формат CSV

Поддержать минимум такие колонки:

```csv
played_at,map_name,result,rounds_for,rounds_against,kills,deaths,assists,kd,adr,kast,rating,headshot_percent,entry_kills,entry_deaths,flash_assists,utility_damage,enemies_flashed,clutches_won,clutches_lost
2026-06-30,Mirage,win,13,9,22,15,4,1.47,91.2,78.0,1.21,48.5,3,2,1,120,4,1,0
```

Если части колонок нет — импорт не должен падать. Отсутствующие поля = null.

## Главные страницы

### `/`

Dashboard:

- общее количество матчей;
- winrate;
- средний K/D;
- средний ADR;
- средний KAST;
- средний rating;
- форма последних 15 матчей;
- сравнение последних 15 vs предыдущих 15;
- лучшие и худшие карты;
- блок “главный фокус тренировки”.

### `/upload`

Форма загрузки CSV/JSON.

### `/matches`

Таблица матчей:

- дата;
- карта;
- результат;
- счёт;
- K/D;
- ADR;
- KAST;
- rating.

Фильтры:
- карта;
- период;
- результат.

### `/report`

Последний coach report.

Кнопка:
- “Сгенерировать новый отчёт”.

## API

Минимальные endpoint:

```http
GET /health
GET /api/matches
POST /api/import/csv
POST /api/import/json
GET /api/analytics/summary
POST /api/reports/generate
GET /api/reports/latest
```

## Analytics engine

Сделать функции:

```python
get_summary(matches)
compare_periods(matches, current_n=15, previous_n=15)
get_map_stats(matches)
detect_weaknesses(summary, comparison, map_stats)
calculate_form_score(matches)
```

### Сравнивать:

- winrate;
- K/D;
- ADR;
- KAST;
- rating;
- entry diff;
- utility damage;
- flash assists;
- deaths per match;
- map winrate.

## Rule-based coach logic

Сделать правила:

1. Если K/D нормальный, но winrate низкий:
   - проблема может быть в low-impact kills или плохих решениях в ключевых раундах.

2. Если ADR падает:
   - не хватает урона, плохие early-round решения или слабый trade/utility impact.

3. Если KAST ниже 70:
   - проблема с выживанием, trade participation или участием в раундах.

4. Если entry_deaths > entry_kills:
   - плохой выбор первых дуэлей.

5. Если utility_damage низкий:
   - тренировать гранаты, особенно на слабых картах.

6. Если карта имеет 10+ матчей и winrate ниже 45:
   - карта требует отдельного плана или временного исключения.

7. Если last15 хуже previous15 по 3+ ключевым метрикам:
   - форма падает, нужен режим стабилизации.

8. Если aim-похожие метрики нормальные, но командные метрики слабые:
   - фокус на позиционирование, трейды, utility, mid-round решения.

## Coach report

Сформировать Markdown-отчёт:

```markdown
# CS2 Coach Report

## Краткий вывод

...

## 3 главные проблемы

1. ...
2. ...
3. ...

## Сильные стороны

...

## Карты

...

## Фокус на 7 дней

...

## План тренировок

### День 1
...

### День 2
...

## Метрики контроля

...
```

Если `OPENAI_API_KEY` есть в `.env`, добавить AI-версию отчёта. Если ключа нет — использовать только rule-based отчёт.

## AI prompt

AI должен получать агрегированный JSON, а не весь сырой список матчей.

Сформировать объект:

```json
{
  "player_profile": {
    "skill_level": "low-mid",
    "goal": "improve consistently in CS2"
  },
  "summary": {},
  "period_comparison": {},
  "map_stats": [],
  "detected_weaknesses": [],
  "available_metrics": []
}
```

Попросить AI:

- не фантазировать;
- не делать выводы по метрикам, которых нет;
- давать практичные рекомендации;
- писать на русском;
- фокусироваться на 7-дневном плане.

## Тесты

Написать тесты:

1. CSV импорт не падает при неполных колонках.
2. Не создаются дубли, если загружается одинаковый матч.
3. Summary считает winrate/KD/ADR/KAST.
4. Compare periods корректно сравнивает последние и предыдущие матчи.
5. Coach rules находят слабые карты и низкий utility impact.
6. Report generator создаёт markdown.

## README

В README указать:

1. Как запустить локально.
2. Как запустить через Docker.
3. Как загрузить sample CSV.
4. Как открыть dashboard.
5. Как сгенерировать отчёт.
6. Какие поля CSV поддерживаются.
7. Что является MVP, а что будет позже.

## Acceptance Criteria

MVP готов, если:

1. Приложение запускается.
2. `/health` отвечает ok.
3. Можно загрузить sample CSV.
4. Матчи отображаются на `/matches`.
5. Dashboard показывает агрегаты и графики.
6. `/report` показывает coach report.
7. Тесты проходят.
8. README понятен.
