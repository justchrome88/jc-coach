# Steam Match Dates

> Status: Supporting Steam/import date policy; not current product, roadmap,
> workflow or source-of-truth.
> Use as task-relevant supporting context only. This file must not override
> `AGENTS.md`, `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md` or current Task Cards.
> Current import and product state truth: `docs/STEAM_IMPORT.md`,
> `docs/CURRENT_STATUS.md` and `docs/project_management/WP_REGISTRY.md`.
> Current workflow truth: `docs/project_management/AGENT_WORKFLOW.md`.
> Navigation/classification: `docs/project_management/DOCS_INDEX.md` and
> `docs/project_management/DOCS_MAP.md`.

## Решение

Для Steam matchmaking/premier матчей точная дата матча берется из Steam/CS2 Game Coordinator metadata, а не из `.dem` файла.

Целевой поток:

1. Пользователь подключает Steam OpenID.
2. Пользователь один раз сохраняет Game Authentication Code и актуальный latest `CSGO-...` share code со Steam Support.
3. Приложение синхронизирует share codes через Valve/Steam слой.
4. Service bot вызывает CS2 Game Coordinator по share code.
5. Game Coordinator возвращает metadata матча, включая `match_time`.
6. `match_time` нормализуется в `app/services/steam_match_metadata.py`.
7. Нормализованная дата записывается в `Match.played_at`.
8. `.dem` парсится только для базовой и глубокой статистики.

Service bot не заменяет пользовательский cursor. Он умеет по уже известному share code получить Steam GC metadata и
demo URL, но не умеет сам перечислить приватную историю матчей пользователя. Для первого sync Valve API требует
`knowncode`; проверка `knowncode=0` на 2026-07-02 вернула `HTTP 412 Precondition Failed`.

Если сохраненный latest share code оказывается старым по `steam_gc_match_time`, приложение должно показать это как
диагностику cursor, а не просить пользователя вставлять share code каждого матча. Правильная модель продукта:
один bootstrap cursor, дальше автоматическая синхронизация.

## Источники Даты

Приоритет источников:

| Приоритет | Источник | `played_at_source` | Статус |
| --- | --- | --- | --- |
| 1 | CS2 Game Coordinator `match_time` | `steam_gc_match_time` | точная дата матча |
| 2 | Заголовок демки, если когда-либо появится надежное поле | `demo_header` | допустимый fallback |
| 3 | mtime файла/CDN/import time | `file_modified_fallback` | неточная дата |

`file_modified_fallback` нельзя показывать или интерпретировать как гарантированную дату игры. Это только техническая дата файла.

## Правила Для Кода

- Steam metadata парсится в `app/services/steam_match_metadata.py`.
- `app/services/demo_parser.py` не должен знать правила Steam-синхронизации.
- `app/services/steam_demo_downloader.py` передает metadata в `import_demo_file(..., steam_metadata=...)`.
- `raw_json.steam_metadata` сохраняется для диагностики.
- UI/API должны отдавать `played_at_source`, чтобы было видно, точная дата или fallback.
- Для Steam-потока не возвращаемся к ручной загрузке `.dem`: без Steam metadata она не дает надежную дату матча.
- Для Steam-потока не возвращаемся к ручному share code каждого матча: это только диагностический/аварийный инструмент,
  основной путь должен оставаться автоматическим после bootstrap.

## Почему Не Дата Из `.dem`

Демка надежно дает карту, раунды, события, урон и статистику игрока. Абсолютное время игры в текущем парсинге не является надежным источником. Если взять дату файла, старые скачанные сегодня демки будут выглядеть как сегодняшние матчи. Именно это и привело к ошибке с неверными dust2/nuke/mirage вместо свежих Cache/Inferno.
