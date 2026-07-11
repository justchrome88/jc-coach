# Metric Truth Inventory

Дата: 2026-07-03.

## 1. Scope

Инвентарь создан для Stage 5 Metric Truth Layer. Цель: зафиксировать текущие метрики, места расчёта, источники, reliability и suppression policy без изменения схемы БД.

Не выполнялось:

- parser hardening;
- Steam cursor/import изменения;
- migration/schema changes;
- recommendation planner;
- AI validator;
- production import/Steam/parser jobs.

## 2. Current Metric Surfaces

| Surface | Files | Metrics / facts |
|---|---|---|
| DB model | `app/db/models.py::Match` | result, score, kills/deaths/assists, kd, adr, kast, rating, swing_score, headshot_percent, entry/early deaths, utility/flash, side splits, raw_json. |
| Analytics | `app/services/analytics.py` | summary, period comparison, dashboard quality, ADR profile, map stats, side winrate, weaknesses. |
| Aim profile | `app/services/aim_stats.py` | ADR, K/D, HS%, opening duel success, weapon breakdown, damage_per_death, multi-kill rounds, coverage/confidence. |
| Mistake detection | `app/services/mistake_detection.py` | low ADR, low KAST, bad entry duels, weak utility, per-match early/entry death signals, crosshair no-data. |
| Recommendations | `app/services/recommendation_tracking.py` | baseline/current entry deaths, early deaths, KAST, ADR, utility damage, flash assists, winrate. |
| AI payload | `app/services/ai_coach.py` | summary, dashboard status, aim profile, comparison, map stats, weaknesses, structured mistakes, recommendations, recent matches. |
| Parser facts | `app/services/demo_parser.py` | player rounds, weapon stats, damage events, duels, grenade events, parser confidence, raw metric confidence. |

## 3. Reliability Classification

| Metric | Reliability | Reason |
|---|---|---|
| result/winrate | trusted | Direct match result when source identity is correct. |
| rounds/kills/deaths/kd | trusted | Basic scoreboard facts; target player selection still matters. |
| assists | medium | Source/parser assist semantics can differ. |
| ADR | medium | Reliable with damage + rounds; CSV/source values still need source trust. |
| KAST | approximate | Trade component is not fully verified. |
| rating | approximate | Source-provided; local formula is not verified. |
| entry kills/deaths | medium | Depends on opening duel event order. |
| early deaths | approximate | May be absent; historical fallback to entry_deaths is not true timing. |
| trade kills | low | Parser trade window/team inference needs hardening. |
| traded deaths | unavailable | No stable stored match metric. |
| utility damage | medium | Depends on utility damage attribution. |
| flash assists/enemies flashed | approximate | Blind/kill correlation is best-effort. |
| grenade_rating | unavailable | No stable formula. |
| aim_rating | unavailable | No stable composite formula. |
| headshot rate | medium | Useful but not crosshair-placement truth. |
| accuracy | low | Needs reliable shots/hits correlation. |
| swing_score | approximate | Heuristic parser-derived impact model. |
| side split metrics | low | Side switching/team inference needs hardening. |
| crosshair placement | unavailable | Needs view-angle/position timeline. |

## 4. Suppression Policy

- `trusted`: allowed for display, diagnosis, recommendation and AI when data exists.
- `medium`: generally allowed, but AI should mention source/coverage caveats.
- `approximate`: warning metric; may be context, not single hard claim.
- `low`: suppressed from hard diagnosis/recommendation.
- `unavailable`: suppressed everywhere except as an explicit data gap.

Specific Stage 5 decisions:

- `early_deaths` is warning-only for recommendation hard scoring.
- `trade_kills` is suppressed from diagnosis/recommendation.
- `traded_deaths` is unavailable.
- `side_split_metrics` are display-warning only and suppressed from diagnosis/recommendation.
- `aim_rating` and `grenade_rating` remain unavailable until formulas exist.

## 5. Code Integration

- Runtime registry: `app/services/metric_truth.py`.
- Recommendation hard-signal checks now consult Metric Truth Layer.
- AI payload now includes metric definitions and suppressed metric lists.
- Tests: `tests/test_metric_truth.py`.

## 6. Later Parser Hardening Targets

- True early-round death timing.
- Traded/untraded death facts.
- KAST trade component confidence.
- Side switching/team side confidence.
- Utility attribution and flash value confidence.
- Weapon-fire/hit correlation for accuracy.
