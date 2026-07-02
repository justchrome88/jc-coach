# Deep parser DEM: ТЗ, реализация и журнал

Дата: 2026-07-02

## Цель

Сделать парсинг `.dem` достаточно полным, чтобы в будущем можно было удалить raw demo-файл после успешного извлечения тренерских данных. На текущем этапе raw `.dem` не удаляются: они остаются контрольным источником для повторной проверки парсера.

## Что умеет текущий `demoparser2`

Установленная версия: определяется в runtime и сохраняется в `demo_parse_artifacts.parser_version`.

Доступные типы данных:

- `parse_header`: технический header демки, включая карту, если поле есть.
- `parse_player_info`: список игроков и SteamID.
- `parse_event`: игровые события: смерти, урон, выстрелы, ослепления, раунды, бомба, pickup/equip, гранаты.
- `parse_grenades`: покадровые траектории гранат.
- `parse_ticks`: выборочные tick-срезы по player/network props.

## Что сохраняем сейчас

Нормализованные таблицы:

- `demo_parse_artifacts`: версия парсера, версия payload, SHA1 демки, счетчики событий, confidence, gaps, полный компактный JSON payload.
- `demo_rounds`: раунды, tick начала/конца/freezetime, победитель, причина окончания, события бомбы.
- `demo_player_rounds`: player-round статистика: kills, deaths, assists, damage, utility damage, flash, opening, KAST.
- `demo_weapon_stats`: оружие по игрокам: shots, hits, kills, deaths, damage, HS%, estimated accuracy.
- `demo_damage_events`: все события урона из `player_hurt`.
- `demo_duels`: все смерти/дуэли из `player_death`, включая opening duel, trade kill, distance, HS, smoke/blind flags.
- `demo_grenade_events`: детонации/старты гранат, flash count, utility damage linkage.

Дополнительно в artifact payload:

- игроки матча и выбранный target player;
- агрегированные траектории гранат: start/end tick, start/end position, max Z, sample count;
- economy/pickup summary;
- target-player summary для тренера.

## Что сознательно не сохраняем полностью

- Полный per-tick movement/view-angle timeline по всем игрокам.
- Полные покадровые траектории гранат строка-в-строку.
- Полную bullet trajectory/spray модель.

Причина: эти данные очень быстро раздувают SQLite до размеров, сопоставимых с raw demo. Сейчас сохраняется полезный тренерский слой: события, агрегаты, дуэли, damage, оружие, гранаты и компактные trajectory summaries.

## Confidence и ограничения

- K/D, deaths, damage events: высокая надежность при наличии `player_death` и `player_hurt`.
- ADR: высокая надежность при наличии damage events и раундов.
- Accuracy: оценочная метрика `hits / weapon_fire`, не bullet-level точность.
- Utility/flash: надежность зависит от наличия `player_blind`, grenade detonations и damage weapon fields.
- Side stats T/CT пока не считаются надежными из-за сложной логики side-switch и team mapping.
- Crosshair placement, first bullet accuracy, spray control требуют отдельной tick/view-angle модели и пока помечены как gaps.

## Реализованный процесс

1. При импорте `.dem` файл копируется в `data/uploads`.
2. `parse_demo` извлекает старые match-level метрики и новый `deep` payload.
3. `matches.raw_json` сохраняет обратную совместимость.
4. `_save_demo_parse_artifacts` очищает старые parsed-таблицы для матча и записывает новую версию.
5. Повторный импорт той же демки не создает дубль матча, но обновляет parsed artifact.
6. UI читает данные из parsed-таблиц, а не из raw `.dem`.

## UI

- Страница матча получила блок `Глубокий парсинг DEM`.
- В блоке показываются счетчики раундов/дуэлей/гранат/оружия, target-player summary, первые дуэли, оружие и гранаты.
- Вкладка `Тренер` получила блок `Готовность DEM-данных`.
- Англоязычные подписи в основных coach-блоках переведены на русский.

## Критерий готовности к удалению raw demo

Raw `.dem` можно будет удалять только после отдельного этапа, когда:

- artifact создан успешно;
- event counts не ниже ожидаемого минимума: есть раунды, смерти, урон, weapon_fire;
- сохранены normalized rows для rounds, duels, damage, player_rounds, weapon_stats;
- по матчу нет critical parser warnings;
- есть отдельная команда/настройка retention policy, а не автоматическое удаление сразу после импорта.

На текущем этапе удаление запрещено.

## Журнал

- 2026-07-02: проведена инспекция `demoparser2` на реальной демке; подтверждены события `player_death`, `player_hurt`, `weapon_fire`, `player_blind`, grenade detonation, bomb events, round events и `parse_grenades`.
- 2026-07-02: добавлена нормализованная схема parsed DEM данных.
- 2026-07-02: расширен parser payload до `PARSER_PAYLOAD_VERSION=2026-07-02.1`.
- 2026-07-02: добавлен UI для deep parser на странице матча и overview на вкладке тренера.
- 2026-07-02: выполнен боевой пере-парсинг текущих `.dem` без удаления raw файлов.

## Боевой прогон 2026-07-02

Итог в базе:

- `matches`: 38;
- `demo_parse_artifacts`: 18 уникальных матчей;
- `demo_rounds`: 385;
- `demo_player_rounds`: 3869;
- `demo_weapon_stats`: 4510;
- `demo_damage_events`: 11445;
- `demo_duels`: 2701;
- `demo_grenade_events`: 3247.

Пути `.dem`:

- найдено 87 путей;
- 35 успешных проходов по путям;
- 52 ошибки на файлах `*_a553be2551_match.dem`.

Разбор ошибок:

- все 52 ошибочных файла имеют размер 7 байт;
- это не полноценные `.dem`, а старые тестовые/битые заглушки;
- `demoparser2` падает на них внутри Rust parser с ошибкой `range end index 16 out of range for slice of length 7`;
- raw файлы не удалялись.

Вывод: валидные текущие демки распарсены и сохранены в боевой базе. Битые 7-byte файлы не считаются пригодными источниками матчевых данных.

## Что нужно от пользователя

Пока ничего. Следующий технический шаг: прогнать текущие реальные `.dem`, сохранить parsed artifacts в боевой базе и проверить страницы.
