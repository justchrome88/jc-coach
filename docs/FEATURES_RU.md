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
- Ручной импорт `.dem` остается как fallback.

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

## Документация

- `WORKLOG.md` ведет инженерный журнал.
- `docs/STEAM_IMPORT_ARCHITECTURE.md` описывает Steam import архитектуру.
- `docs/DEMO_STORAGE_TZ.md` описывает целевой lifecycle raw demo.
- `docs/FEATURES_RU.md` содержит список внедренных фич.
