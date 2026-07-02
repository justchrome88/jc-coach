# Внедренные фичи JC Coach

## Авторизация и защита

- Внутренний web login/register для приложения.
- Внешняя nginx Basic Auth защита для домена `jcnodex.ru`.
- `robots.txt` полностью запрещает индексацию на время разработки.

## Steam import

- Пользователь подключает Steam через официальный Steam OpenID.
- Пользователь один раз вводит:
  - код последнего соревновательного матча `CSGO-...`;
  - Game Authentication Code из Steam Support.
- Пользователь не вводит Steam пароль, Steam Guard, QR или refresh token.
- Серверный Steam Web API key хранится в `.env`; пользователю не нужно выпускать свой ключ.
- Кнопка “Обновить и скачать демки”:
  - ставит `steam_import_all` job;
  - сразу возвращает страницу;
  - фоновая задача синхронизирует share codes, получает demo URL через service bot, скачивает `.dem.bz2`, распаковывает `.dem` и импортирует матч.
- Прогресс доступен:
  - в `/settings/imports`;
  - через `GET /api/steam/import/overview`.

## Steam service bot

- Отдельный Steam bot аккаунт используется только для запроса CS2 Game Coordinator по share code.
- Bot refresh token хранится локально в `data/steam_bot_credentials/`.
- Service bot не является аккаунтом пользователя и не должен иметь ценный inventory.
- Статус настройки: `GET /api/steam/demo-downloader/status`.

## Demo parsing

- `.dem` файлы импортируются через `demoparser2`.
- В `matches` сохраняются основные match metrics.
- В `matches.raw_json` сохраняется parsed payload, включая player, header, event counts, confidence и warnings.
- В parsed payload теперь сохраняются `aim_summary`, `weapon_breakdown` и `aim_data_gaps`.
- Ручной импорт `.dem` остается как fallback.

## AI coach persistence

- AI report сохраняется в `coach_reports` как `report_type=ai_coach`.
- В `report_json` сохраняется:
  - provider;
  - status;
  - payload hash;
  - payload summary;
  - payload snapshot;
  - content length;
  - handoff metadata.
- `/coach` показывает последний AI report и историю последних AI reports.
- API:
  - `GET /api/coach/ai/result/latest`;
  - `GET /api/coach/ai/results`;
  - `POST /api/coach/ai/result`;
  - `POST /api/coach/ai/generate`.

## Multi-category recommendations

- Системные категории: survival, aim, grenades, map.
- Для каждой цели есть baseline, target, progress score, green/yellow/red/gray оценки матчей.
- `/coach` показывает:
  - active category cards;
  - lifecycle actions: Extend, Restart, Pause, Done, Archive;
  - сводку категорий;
  - историю целей.
- API:
  - `GET /api/recommendations`;
  - `GET /api/recommendations/history`;
  - `GET /api/recommendations/categories`;
  - `POST /api/recommendations/{id}/status`;
  - `POST /api/recommendations/{id}/extend`;
  - `POST /api/recommendations/categories/{category}/restart`.

## Aim stats

- Добавлен честный aim profile без псевдометрик:
  - ADR;
  - K/D;
  - HS%;
  - damage per death;
  - opening duel success;
  - multi-kill rounds;
  - weapon breakdown: kills, headshots, deaths, damage, HS%.
- `GET /api/analytics/aim` возвращает aggregate aim profile.
- Aim profile показан на `/stats`, `/coach` и странице матча.
- Accuracy, first bullet accuracy, spray control, TTK и crosshair placement явно помечены как data gaps до появления надежных shot/view/position данных.

## Demo storage lifecycle

- Целевая схема: `download -> parse -> verify parsed payload -> delete raw .dem`.
- Сейчас raw `.dem` не удаляются, потому что финальный набор метрик еще не утвержден.
- Добавлена страница `/settings/storage`:
  - общий размер demo storage;
  - количество файлов;
  - referenced/unreferenced/missing/suspicious файлы;
  - top больших файлов;
  - будущие кандидаты на удаление raw `.dem`;
  - manifest path.
- API:
  - `GET /api/storage/demos`;
  - `POST /api/storage/demos/manifest`.
- Manifest пишется в `data/reports/demo_storage_manifest.json` и не коммитится.

Текущее live-состояние на 2026-07-01 после инспекции:

- `.dem` файлов в `data/uploads`: 61.
- Общий размер raw demo: около 4.18 GB.
- Уникально привязанных raw demo файлов: 16.
- Match rows со ссылкой на demo: 32.
- Будущих кандидатов на удаление после verified payload: 16 файлов.
- Потенциальная будущая экономия после включения verified-delete: около 3.8 GB.
- Удаление raw `.dem` выключено.

## Документация

- `WORKLOG.md` ведет инженерный журнал.
- `docs/STEAM_IMPORT_ARCHITECTURE.md` описывает Steam import архитектуру.
- `docs/DEMO_STORAGE_TZ.md` описывает целевой lifecycle raw demo.
- `docs/FEATURES_RU.md` содержит список внедренных фич.
- `docs/FEATURE_ROADMAP_SCORING.md` и `docs/feature_roadmap_scoring_ru.xlsx` содержат roadmap/scoring по конкурентным фичам.

## Ближайший технический фокус

- Утвердить набор метрик/raw-срезов, достаточный для повторного анализа без raw `.dem`.
- Добавить статус `parsed_payload_verified`.
- Расширить demo parser payload по раундам, дуэлям, utility, side stats, timing и позициям там, где данные надежны.
- После этого включать raw `.dem` delete policy для успешно проверенных импортов.
- Довести Steam worker до durable scheduler/retry модели.
