# Какие данные вытаскивать из матчей/демок CS2

## Уровень 1: сухие данные матча

Эти данные нужны уже в MVP, даже если они загружаются вручную через CSV/JSON.

- дата матча;
- карта;
- режим;
- счёт;
- победа/поражение;
- раунды за/против;
- kills;
- deaths;
- assists;
- K/D;
- ADR;
- KAST;
- rating;
- swing / round swing;
- headshot %;
- entry kills;
- entry deaths;
- flash assists;
- utility damage;
- clutches won/lost.

## Уровень 2: данные по сторонам

Для тренера важнее не общий K/D, а где именно провал.

- T-side rounds won/lost;
- CT-side rounds won/lost;
- T-side kills/deaths/ADR;
- CT-side kills/deaths/ADR;
- T-side opening deaths;
- CT-side opening deaths;
- bomb plant participation;
- retake participation.

## Уровень 3: round-level данные

Нужно для будущего качественного тренера.

- номер раунда;
- сторона;
- экономика команды;
- оружие игрока;
- результат раунда;
- был ли игрок жив на конец раунда;
- время смерти;
- время первого контакта;
- first kill / first death;
- trade был/не был;
- clutch situation;
- round swing delta;
- bomb plant/defuse;
- damage в раунде;
- utility в раунде.

## Уровень 4: event-level данные из demo

- kill events;
- death events;
- damage events;
- grenade throws;
- flash events;
- bomb events;
- round start/end;
- player positions;
- weapon fired;
- reloads, если доступно;
- footsteps/noise, если доступно;
- dropped/picked weapons, если полезно.

## Уровень 5: позиционные данные

Для heatmaps и будущего 2D viewer:

- player x/y/z;
- tick/time;
- map;
- side;
- alive/dead;
- event type;
- killer/victim position;
- grenade landing position;
- bomb plant position.

## Главные метрики тренера

### Aim / Duel

- K/D;
- headshot %;
- opening duel success;
- time to kill, если доступно;
- damage per death;
- kills per round;
- deaths per round.

### Impact

- ADR;
- KAST;
- first kills;
- multi-kills;
- clutch wins;
- trade kills;
- round win contribution.
- swing score.

#### Swing / Round Swing

Цель: оценить, насколько действия игрока двигали раунд к победе, а не просто увеличивали K/D.

Внешние ориентиры:

- FACEIT Round Swing: изменение win probability от действий игрока, включая урон, utility/flash, bomb actions, trade и экономический контекст.
- HLTV Rating 3.0 Round Swing: вклад действий в изменение вероятности победы в раунде; учитывает kill impact, damage share, flash assists, trade и экономику.

Наша текущая формула: `jc_swing_v1`.

Что считаем сейчас:

- для каждого раунда строится состояние `own_alive`, `enemy_alive`, `bomb_planted`;
- перед событием считается estimated win probability;
- после death/bomb event состояние обновляется и считается новая probability;
- разница probability считается swing delta;
- игрок получает credit за:
  - kill;
  - death;
  - assist;
  - flash перед kill;
  - damage share по victim;
  - bomb plant/defuse/explosion;
- итог `swing_score` = средний вклад в процентных пунктах на раунд.

Где хранится:

- `matches.swing_score`;
- `raw_json.swing_summary`;
- `demo_parse_artifacts.payload_json.deep.target_player_summary` в следующих версиях можно расширять под swing breakdown.

Confidence:

- `medium`, если есть player team mapping, `player_death` и `round_end`;
- `low`, если нет team mapping или round events.

Ограничения:

- это не копия закрытой модели FACEIT/HLTV;
- пока нет полноценной economy-adjusted модели;
- нет map-specific probability model;
- side switching требует дальнейшей валидации;
- показатель полезен как coach-сигнал, но должен интерпретироваться вместе с ADR/KAST/entry/utility.

### Survival / Decisions

- early deaths;
- deaths without trade;
- deaths with bomb;
- deaths in advantage;
- late-round survival;
- repeated death zones.

### Utility

- HE damage;
- molotov damage;
- flash assists;
- enemies flashed;
- smokes thrown;
- useful utility per round;
- utility before death;
- unused utility at death.

### Teamplay

- trade participation;
- traded deaths;
- spacing;
- flash assists;
- support utility;
- survival in man advantage.

## Что выводить на dashboard

### Верхние карточки

- matches;
- winrate;
- K/D;
- ADR;
- KAST;
- form score;
- main weakness;
- weekly focus.

### Графики

- K/D over time;
- ADR over time;
- KAST over time;
- rating/form over time;
- winrate by map;
- T/CT winrate by map;
- utility impact over time.

### Таблицы

- последние матчи;
- карты;
- слабые карты;
- лучшие карты;
- топ проблем;
- тренировки на неделю.

## Как AI должен использовать данные

AI получает агрегаты и уже найденные weak points.

AI не должен:
- сам придумывать статистику;
- делать выводы без данных;
- говорить “плохой aim”, если aim-метрик нет;
- давать общие советы уровня “играй лучше”.

AI должен:
- выбрать 1 главный фокус;
- объяснить причину;
- дать 7-дневный план;
- указать метрики контроля;
- отделить уверенные выводы от гипотез.
