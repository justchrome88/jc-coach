# План доведения сложных фич до 100%

Этот план описывает пошаговое внедрение и отладку фич, которые нельзя честно закрыть одной UI-правкой. Каждая фича считается готовой на 100%, когда выполнены критерии в блоке `Definition of Done`.

## 1. Загрузка официального DEM

Текущий статус: базовый импорт работает, реальный `.dem` матч попадает в список игр, считаются map/result/score/KD/ADR/KAST/entry/utility best-effort.

### Этапы

| Шаг | Что сделать | Проверка |
|---|---|---|
| 1 | Добавить экран результата импорта DEM: выбранный игрок, карта, счет, дата, kills/deaths/ADR/KAST, confidence | После загрузки пользователь видит не только `Imported 1`, а полный импорт-результат |
| 2 | Добавить player picker перед финальным сохранением, если parser нашел несколько игроков | На одной demo можно выбрать JC/другого игрока без повторной загрузки файла |
| 3 | Перевести тяжелый parse в background job | Большой DEM не блокирует HTTP request и показывает статус `queued/running/done/failed` |
| 4 | Сохранить parser evidence в `raw_json`: player, header, event counts, confidence warnings | У каждого DEM-матча можно открыть технические детали импорта |
| 5 | Расширить unit/integration tests на 3-5 реальных DEM-файлов | Все тестовые demos импортируются стабильно и не создают дубли |
| 6 | Сделать UX ошибок: неизвестный формат, нет событий, игрок не найден, duplicate | Каждая ошибка дает понятное действие пользователю |

### Definition of Done

- DEM можно загрузить через web panel.
- Пользователь может выбрать игрока, если auto-detect ошибся.
- Большой файл не роняет и не подвешивает web request.
- После импорта открывается match detail с данными и confidence.
- Duplicate DEM не создает лишние матчи и лишние копии файла.
- Есть regression tests на успешный импорт, duplicate, player selection и parse failure.

## 2. Автоматический импорт матчей

Текущий статус: не реализовано.

### Этапы

| Шаг | Что сделать | Проверка |
|---|---|---|
| 1 | Выбрать первый источник: Steam share codes, FACEIT API или локальный demo inbox watcher | Зафиксирован один MVP-flow без распыления |
| 2 | Добавить таблицу `import_jobs` со статусами и ошибками | В UI видна история попыток импорта |
| 3 | Реализовать ручной запуск sync из web panel | Пользователь нажимает кнопку и видит найденные новые матчи |
| 4 | Добавить scheduler для периодической проверки | Новые матчи подтягиваются без ручного действия |
| 5 | Сделать idempotency через external IDs/share codes | Повторный sync не создает дубли |
| 6 | Добавить observability: logs, counters, last successful sync | Ошибки импорта можно диагностировать без доступа к коду |

### Definition of Done

- Пользователь подключает источник матчей один раз.
- Новые матчи подтягиваются вручную и автоматически.
- У каждого job есть статус, длительность, ошибка и список созданных матчей.
- Повторный импорт безопасен.
- Есть тесты на success, duplicate, API failure и retry.

## 3. Aim stats

Текущий статус: есть только простые производные метрики: K/D, HS%, частично weapon events.

### Этапы

| Шаг | Что сделать | Проверка |
|---|---|---|
| 1 | Зафиксировать MVP-набор aim метрик: HS%, opening duel success, damage per death, multi-kill rounds, low-impact deaths | Метрики понятны пользователю и считаются из текущих событий |
| 2 | Добавить weapon breakdown: kills/deaths/damage/headshots по оружию | Match detail показывает сильные/слабые типы оружия |
| 3 | Добавить time-to-damage / time-to-kill, если события DEM позволяют надежно считать timing | На тестовых demos значения стабильны и объяснимы |
| 4 | Добавить crosshair placement только после появления координат/углов и карты | Не внедрять псевдометрику без надежных данных |
| 5 | Сделать aim dashboard и trend по aim метрикам | Пользователь видит прогресс aim отдельно от общей формы |
| 6 | Связать aim weakness с coach recommendations | При плохом aim формируется конкретный drill/план |

### Definition of Done

- Aim stats считаются из DEM и отображаются в match detail.
- Есть агрегаты по последним 15/30 матчам.
- Метрики имеют confidence и не показываются, если данных недостаточно.
- Есть тесты на weapon breakdown, HS%, opening duels и missing data.

## 4. Mistake detection

Текущий статус: есть базовые rule-based weakness detection и coach focus.

### Этапы

| Шаг | Что сделать | Проверка |
|---|---|---|
| 1 | Создать каталог mistake types: early death, bad entry, low ADR, low KAST, weak utility, weak map, economy throw | Каждая ошибка имеет описание, evidence и severity |
| 2 | Добавить evidence model: match_id, round, metric, threshold, explanation | Ошибка не просто текст, а ссылка на конкретные данные |
| 3 | Перевести текущие rules на mistake objects | Coach page показывает структурированные ошибки |
| 4 | Добавить confidence и suppression правил | Система не ругает игрока при недостатке данных |
| 5 | Добавить per-match mistakes на match detail | В каждом матче видно, что именно пошло плохо |
| 6 | Добавить feedback loop: пользователь помечает ошибку полезной/неполезной | Можно улучшать правила без переписывания всего |
| 7 | Позже подключить AI explanation поверх structured evidence | AI объясняет уже найденные факты, а не придумывает их |

### Definition of Done

- Ошибки структурированы и связаны с матчами/метриками.
- Каждая ошибка имеет severity, confidence и evidence.
- Coach report использует эти ошибки как основу рекомендаций.
- Есть тесты на каждое правило, missing data и priority ordering.

## Рекомендуемый порядок работ

1. Довести DEM import result + match detail до production-like UX.
2. Добавить parser confidence и сохранить evidence.
3. На базе evidence расширить ADR/KAST/entry/utility корректность.
4. Внедрить structured mistake detection.
5. Затем делать Aim stats.
6. Автоматический импорт запускать после того, как ручной DEM-flow станет надежным.
