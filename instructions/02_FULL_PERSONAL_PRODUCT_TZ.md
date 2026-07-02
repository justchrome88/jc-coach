# HISTORICAL / DEPRECATED

This original product TZ is retained for context. Current milestone scope is governed by `docs/PROJECT_CONTROL.md` and `docs/CURRENT_MILESTONE.md`.

# Полное ТЗ: CS2 Personal Coach для личного использования

## 1. Видение продукта

Создать красивый личный веб-сайт для анализа прогресса в CS2.

Это не публичный SaaS на первом этапе. Это приватный продукт для одного пользователя, но с архитектурой, которую можно позже расширить до беты для друзей и затем до коммерческого продукта.

Главная ценность: не просто статистика, а персональный AI-тренер, который превращает матчи и демки в понятные выводы и тренировочный план.

## 2. Основные сценарии

### Сценарий 1: вход через Steam

Пользователь нажимает “Войти через Steam”, подтверждает SteamID, после чего сайт показывает профиль игрока и его матчи.

Важно:
- Steam login использовать только для подтверждения личности и получения SteamID.
- Не хранить пароль Steam.
- Не просить у пользователя Steam-логин/пароль.
- Использовать OpenID-подход, если он применим для веб-авторизации.

### Сценарий 2: загрузка демки вручную

Пользователь загружает `.dem` или архив с `.dem`.

Система:
1. сохраняет файл;
2. ставит задачу на парсинг;
3. извлекает события;
4. считает метрики;
5. показывает матч в дашборде;
6. создаёт отчёт тренера.

### Сценарий 3: загрузка CSV/JSON

Пользователь экспортирует данные из внешнего сервиса или подготавливает файл вручную.

Система импортирует данные, чтобы можно было быстро получить аналитику даже без полноценного demo parsing.

### Сценарий 4: AI coach report

Пользователь нажимает “Сгенерировать отчёт”.

Система:
1. берёт последние матчи;
2. сравнивает периоды;
3. анализирует карты, стороны, смерти, utility, entry;
4. выдаёт главные проблемы;
5. даёт 7-дневный тренировочный план.

## 3. Архитектура

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Celery/RQ/Arq для фоновых задач
- Redis как broker
- Docker Compose
- отдельный worker для demo parsing

### Frontend

Первый вариант:
- server-rendered Jinja2 + HTMX + Chart.js

Дальше можно перейти на:
- Next.js / React
- API backend отдельно

### Storage

- локальное файловое хранилище на VPS для MVP;
- позже S3-compatible storage: MinIO, Selectel, Backblaze, AWS S3.

Хранить:
- загруженные демки;
- сжатые обработанные JSON;
- отчёты;
- возможно thumbnails/heatmap images.

## 4. Модули

### 4.1 Steam auth module

Задачи:

- вход через Steam;
- получение SteamID;
- создание локального пользователя;
- привязка Steam-профиля;
- хранение avatar/name/profile_url, если доступно через Steam Web API;
- возможность вручную обновить профиль.

Ограничения:

- не обещать автоматическую полную историю матчей через обычный Steam Web API;
- автоматическая загрузка матчей CS2 может потребовать share codes/auth code/Game Coordinator-подхода;
- это отдельная сложная задача, не смешивать с первым MVP.

### 4.2 Match ingestion module

Источники матчей:

1. CSV/JSON upload.
2. Manual `.dem` upload.
3. Steam/share-code import — later.
4. FACEIT import — later.
5. Scope/Leetify-like export — если пользователь вручную даст файл.

### 4.3 Demo parser module

Использовать одну из библиотек:
- demoparser2;
- awpy;
- либо другой актуальный инструмент после проверки.

Минимально извлекать:

- kills;
- deaths;
- assists;
- headshots;
- damage;
- flash assists;
- utility usage;
- grenade damage;
- round start/end;
- bomb plant/defuse;
- player positions по tick/interval;
- team side;
- economy, если доступно;
- weapon usage;
- trade kills/deaths;
- opening duels;
- clutches.

### 4.4 Analytics module

Считать:

#### Общие метрики

- matches played;
- winrate;
- K/D;
- kills per round;
- deaths per round;
- ADR;
- KAST;
- rating-like score;
- headshot %;
- impact score;
- consistency score.

#### Entry

- opening kills;
- opening deaths;
- opening duel success;
- entry attempts;
- entry impact.

#### Trade

- traded deaths;
- trade kills;
- trade participation;
- time-to-trade.

#### Utility

- HE damage;
- molotov damage;
- flash assists;
- enemies flashed;
- self/team flash issues, если возможно;
- smokes used;
- useful utility score.

#### Clutch

- clutch attempts;
- clutches won;
- 1v1/1v2/1v3;
- post-plant performance.

#### Map stats

- winrate by map;
- K/D by map;
- ADR by map;
- T-side winrate;
- CT-side winrate;
- weak maps;
- best maps.

#### Round phases

- early-round deaths;
- mid-round impact;
- late-round survival;
- post-plant mistakes;
- retake performance.

#### Position analysis

- death heatmap;
- kill heatmap;
- common death zones;
- common kill zones;
- map zones by side.

### 4.5 AI coach module

AI получает агрегированные данные и выдаёт:

1. Краткий диагноз.
2. Главные сильные стороны.
3. Главные слабости.
4. Карты для фокуса.
5. Стороны/позиции для фокуса.
6. Что тренировать.
7. Что прекратить делать.
8. 7-дневный план.
9. Метрики контроля.
10. Следующий review checklist.

AI не должен:
- выдумывать данные;
- ссылаться на несуществующие метрики;
- давать общие советы без привязки к данным;
- притворяться профессиональным тренером без оговорок.

### 4.6 2D demo viewer — later

Полноценный viewer не делать в первом MVP.

Будущая версия:

- карта сверху;
- траектории игроков;
- события убийств;
- utility overlay;
- переключение раундов;
- timeline;
- фильтр по игроку;
- heatmaps;
- death replay.

Сначала можно сделать статичные heatmaps, а не live viewer.

## 5. Дашборды

### Главная

- карточка профиля;
- форма за последние 15/30 матчей;
- рейтинг формы;
- главный тренерский вывод;
- кнопка “Сгенерировать отчёт”.

### Progress

- графики K/D, ADR, KAST, rating;
- сравнение периодов;
- тренды.

### Maps

- таблица карт;
- winrate;
- side winrate;
- слабые карты;
- рекомендации по картам.

### Utility

- damage;
- flashes;
- smoke/molotov usage;
- utility score;
- что тренировать.

### Death Review

- ранние смерти;
- частые зоны смертей;
- death reasons, если можно классифицировать;
- советы.

### Coach Report

- отчёт за неделю;
- план;
- список задач;
- чеклист.

## 6. Красивый сайт

Дизайн-направление:

- dark UI;
- стиль аналитического esport-dashboard;
- акценты: зелёный/синий/фиолетовый;
- карточки метрик;
- графики;
- компактные таблицы;
- блок “Coach says”.

В MVP лучше не уходить в сложный дизайн. Но сайт должен выглядеть приятно и мотивировать пользоваться им.

## 7. Безопасность и приватность

- Не хранить пароли Steam.
- Не загружать приватные ключи в репозиторий.
- `.env` не коммитить.
- Ограничить доступ к сайту базовой авторизацией или приватным VPN, пока это личный продукт.
- Загруженные демки считать приватными.
- Не публиковать чужие данные.

## 8. Этапы

### Этап 1

CSV/JSON import + dashboard + coach report.

### Этап 2

Manual demo upload + parser.

### Этап 3

Steam auth + профиль.

### Этап 4

Semi-auto match import/share codes.

### Этап 5

Heatmaps.

### Этап 6

2D viewer.

### Этап 7

Friends beta.

### Этап 8

Коммерческая проверка.

## 9. Критерий перехода к коммерции

Думать о продаже только если:

1. продукт полезен владельцу проекта;
2. 3–5 друзей/тестеров получили полезные выводы;
3. люди возвращаются после матчей;
4. есть повторяемый weekly report;
5. понятна стоимость обработки одного пользователя;
6. есть минимум 1–2 человека, готовых заплатить.
