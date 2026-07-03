# Metrics

Last updated: 2026-07-03.

Этот документ является каноническим описанием правды по метрикам. Runtime-источник для code-level политики: `app/services/metric_truth.py`.

## Current Truth

Stage 5 вводит Metric Truth Layer без изменений схемы БД. Каждая важная метрика получает:

- stable metric id;
- source;
- formula/definition;
- reliability;
- limitations;
- usage policy для `display`, `diagnosis`, `recommendation`, `ai`.

Уровни reliability:

| Level | Meaning |
|---|---|
| `trusted` | Можно использовать как hard evidence при наличии данных. |
| `medium` | Можно использовать, но учитывать source/parser coverage. |
| `approximate` | Можно показывать и передавать в AI только с предупреждением; не использовать как единственную жёсткую причину. |
| `low` | Только осторожный display/warning, не hard diagnosis/recommendation. |
| `unavailable` | Не использовать как текущую метрику. |

Usage decision:

| Decision | Meaning |
|---|---|
| `allowed` | Допустимо для hard claim в указанном usage. |
| `warn` | Допустимо как контекст с явным предупреждением, но не как hard claim. |
| `suppressed` | Нельзя использовать для указанного usage. |

## Core Metric Table

| Metric id | Reliability | Source / formula | Usage summary | Limitations |
|---|---|---|---|---|
| `result` / `winrate` | `trusted` | `Match.result`; winrate = wins / matches. | Allowed for all usage. | Зависит от корректной идентичности матча и результата. |
| `round_score` | `trusted` | `rounds_for:rounds_against`. | Allowed for all usage. | Side attribution ниже по доверию, чем общий score. |
| `kills`, `deaths` | `trusted` | Match fields or parser player-round aggregation. | Allowed for all usage. | Нужен корректный target player. |
| `kd_ratio` | `trusted` | kills / deaths. | Allowed for all usage. | Не объясняет role/map context. |
| `adr` | `medium` | total damage / rounds. | Hard recommendation allowed; AI should warn. | Надёжен только при корректных damage events и round count. |
| `kast` | `approximate` | K/A/survive/trade participation. | Warning metric for diagnosis/recommendation/AI. | Trade component не fully reliable. |
| `hltv_rating` | `approximate` | Source-provided rating. | Warning metric. | Это не локально проверенная HLTV 2.0 formula. |
| `entry_kills`, `entry_deaths` | `medium` | Parser/source opening duel facts. | Allowed for diagnosis/recommendation, AI warns. | Зависит от event order и target player. |
| `early_deaths` | `approximate` | Deaths inside parser early-round timing window when `round_freeze_end` or `round_start` anchors are available. | Warning metric; not hard scoring. | Если timing anchors отсутствуют, значение не заполняется; fallback в `entry_deaths` запрещён. |
| `trade_kills` | `low` | Parser death-event order. | Suppressed from hard diagnosis/recommendation. | Trade window/team-side inference needs parser hardening. |
| `traded_deaths` | `unavailable` | Не хранится как reliable match metric. | Suppressed. | Нельзя делать выводы о traded/untraded death rate. |
| `utility_damage` | `medium` | Grenade damage attribution. | Allowed, AI warns. | Зависит от parser utility weapon/damage support. |
| `flash_assists`, `enemies_flashed` | `approximate` | Blind/kill correlation and blind events. | Warning metrics. | Не доказывают team impact без контекста. |
| `grenade_rating` | `unavailable` | Stable formula отсутствует. | Suppressed. | Использовать отдельные utility metrics. |
| `headshot_rate` | `medium` | headshot kills / kills. | Warning for diagnosis/recommendation/AI. | Не является crosshair-placement metric. |
| `accuracy` | `low` | hits / shots from weapon stats. | Display warning only. | Нужна надёжная weapon_fire/hit correlation. |
| `aim_rating` | `unavailable` | Stable formula отсутствует. | Suppressed. | Использовать ADR/HS/opening-duels по отдельности. |
| `swing_score` | `approximate` | Parser heuristic win-probability deltas. | Warning metric. | Heuristic model, depends on parser completeness. |
| `side_split_metrics` | `low` | `side_t_*`, `side_ct_*`. | Display warning only; suppressed for diagnosis/recommendation. | Side switching/team inference low confidence. |
| `crosshair_placement` | `unavailable` | Needs view-angle/position timeline. | Suppressed. | Must remain data gap. |

## Runtime Policy

- `app/services/metric_truth.py` is the code registry.
- Unknown metric id returns safe `unavailable` behavior.
- Low/unavailable metrics are suppressed from hard diagnosis/recommendation.
- Approximate metrics can be displayed and passed to AI only with warning semantics.
- `early_deaths` must not fallback to `entry_deaths`; parser can fill it only when timing anchors exist.
- Side split metrics must not drive diagnosis/recommendation until parser confidence improves.

## Current Integration

- Recommendation evaluation consumes Metric Truth Layer for hard-signal checks.
- Survival recommendations no longer treat `early_deaths` as a hard success/failure signal.
- AI payload includes selected metric definitions and suppressed metric lists.
- Diagnosis registry is still future work; existing rule-based diagnosis remains partial and must not be treated as final planner logic.

## Next Work

- Parser hardening for KAST/trade, traded deaths, side switching and utility attribution.
- Diagnosis registry from verified problems.
- Recommendation planner that chooses one primary recommendation from verified evidence.
- AI output schema/validator that rejects unsupported metric claims.
