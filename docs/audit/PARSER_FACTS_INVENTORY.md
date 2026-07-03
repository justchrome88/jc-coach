# Parser Facts Inventory

Дата: 2026-07-03.

## 1. Scope

Инвентарь создан для Stage 6 Parser facts & confidence hardening.

Не выполнялось:

- production parser jobs;
- production Steam/import jobs;
- production demo reparsing;
- schema changes / migrations;
- Steam cursor truth;
- AI validator;
- recommendation planner;
- UI redesign / viewer / heatmaps / clips.

## 2. Parser Fact Surfaces

| Surface | File / storage | Current facts | Confidence status |
|---|---|---|---|
| Match summary | `app/services/demo_parser.py::parse_demo()` -> `Match` | kills, deaths, assists, ADR, KAST, entry kills/deaths, early deaths, utility/flash, score, side fields | Mixed; confidence stored in `raw_json.metric_confidence`. |
| Parser metadata | `raw_json`, `DemoParseArtifact.confidence_json` | `metric_confidence`, `parser_confidence`, `warnings` | Exists; Stage 6 adds clearer weak-fact keys/warnings. |
| Deep rounds | `DemoRound` | round number, ticks, winner side, bomb context | Useful for context; side inference still low. |
| Player rounds | `DemoPlayerRound` | kills/deaths/assists/damage/utility/opening/KAST per round | Good event aggregation, but KAST trade component incomplete. |
| Duels | `DemoDuel` | attacker/victim, tick, opening duel, `trade_kill` approximation | Trade kill low confidence; traded death facts unavailable. |
| Damage | `DemoDamageEvent` | damage health/armor, weapon, attacker/victim | Supports ADR/utility, but attribution varies by event fields. |
| Grenades | `DemoGrenadeEvent` | grenade events, flashes, utility damage samples | Useful but not enough for stable `grenade_rating`. |
| AI payload | `app/services/ai_coach.py` | match facts and metric truth metadata | Consumes warnings/metadata; no AI validator yet. |
| Recommendations | `app/services/recommendation_tracking.py` | entry deaths, early deaths, KAST, ADR, utility, flash | Hard-signal gating comes from Metric Truth Layer. |

## 3. Stage 6 Findings

### Early deaths

Before Stage 6, parser-level `match.early_deaths` was always set to `stats["entry_deaths"]`.

Stage 6 changes this:

- `early_deaths` is computed only when parser has timing anchors from `round_freeze_end` or `round_start`;
- death tick must fall inside the early-round timing window;
- if anchors are missing, `early_deaths` is `None`;
- confidence is `medium` only when value can be derived, otherwise `low`;
- Metric Truth remains `approximate` and warning-only.

### Entry deaths

`entry_deaths` remains first-death/opening-duel based. It is not the same fact as early-round timing. Reliability remains `medium`.

### Trade / KAST / traded deaths

- `trade_kill` exists on `DemoDuel`, but it is still a low-confidence approximation based on nearby death order.
- `traded_deaths` and `untraded_deaths` are not stored as reliable match facts.
- KAST exists, but trade component is incomplete; parser confidence now has `kast_trade_component: low`.

### Side split / team inference

Score can use player team events or player info. Side split fields on `Match` remain unset for parser imports, and `side_stats` remains `low`.

### Utility / flash

- `utility_damage` is backed by damage events and utility weapon matching; reliability remains `medium`.
- `flash_assists` / `enemies_flashed` are approximate due to blind/kill correlation and event-field variability.
- `grenade_rating` remains unavailable; no stable formula was introduced.

## 4. Metric Truth Impact

No reliability level was upgraded in Stage 6.

Intentional non-upgrades:

- `early_deaths`: remains `approximate` because timing window and anchor availability are still parser-dependent.
- `trade_kills`: remains `low`.
- `traded_deaths`: remains `unavailable`.
- `side_split_metrics`: remains `low`.
- `flash_assists` / `enemies_flashed`: remain `approximate`.
- `grenade_rating`: remains `unavailable`.

## 5. Later Work

- Validate tickrate/timing window against real fixture corpus before any reliability upgrade.
- Implement traded/untraded death facts only if existing parser events can support them without schema shortcuts.
- Improve team-side inference before side splits drive diagnosis/recommendations.
- Add diagnosis registry and planner after parser confidence is stable enough.
