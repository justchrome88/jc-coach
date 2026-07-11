# Metrics

Last updated: 2026-07-08.

> Status: supporting legacy runtime-policy summary. Canonical metric identity,
> contracts, assurance state, and investigations now live in `docs/metrics/`.
> Runtime policy remains in `app/services/metric_truth.py` pending versioned
> reconciliation; neither source overrides disputed entries in the canonical registry.

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
- Match date truth follows the same confidence rule: exact match date for primary Steam import means Steam GC `match_time` / `steam_gc_match_time`. Demo header or file modified time must not be treated as exact for Steam import freshness, diagnosis windows or UI claims.

## Metric Confidence Evidence Contract

`metric_confidence` is mandatory when a metric is used as recommendation,
evaluation or AI coach evidence for a hard claim. It must reflect the combined
confidence of Metric Truth reliability, source trust, sample size, aggregation
quality, date/window quality and CS2 domain availability.

Contract meanings:

| `metric_confidence` | Meaning | Hard-advice behavior |
|---|---|---|
| `high` | Metric and source are accepted for the claim, samples/windows pass and no material domain caveat weakens the result. | May support hard diagnosis, recommendation or progress when all other evidence links exist. |
| `medium` | Metric is usable but source coverage, parser coverage, mixed-source aggregation or sample size requires a caveat. | May support bounded advice with visible caveats; should not be the sole basis for strong progress wording. |
| `low` | Metric is approximate, sparse, source-limited, display-only or otherwise weak for the claim. | Context only; blocked from hard diagnosis, recommendation, evaluation success/failure or confident AI advice. |
| `unavailable` | Metric/model/source is unavailable or suppressed for the claim. | Suppressed from hard advice and evidence arrays. |

Missing `metric_confidence` is equivalent to insufficient evidence for hard
advice. It may be shown as context only if the surrounding surface makes the
limitation visible.

## Source Trust And Aggregation Policy

This section is the accepted docs/design policy for mixed metric sources. It
does not change runtime behavior by itself. Code, tests, fixtures, confidence
labels or regression gates that enforce this policy require separate scoped
tasks.

### Source Trust Registry

Every current or future source that can feed a metric must be registered before
hard coach advice may rely on it. The registry entry must define:

- source id and human label;
- source category and owner service/import path;
- accepted facts and explicitly unsupported facts;
- date/freshness source and whether it is exact, approximate or unavailable;
- metric categories it may support;
- source trust tier;
- required caveats and suppression rules;
- conflict behavior when another source provides the same fact;
- required evidence before promotion from context-only to hard-advice use.

Source trust tiers are separate from per-metric reliability. Hard advice
requires both an accepted source tier and an accepted Metric Truth usage
decision.

| Source trust tier | Meaning | Hard advice behavior |
|---|---|---|
| `trusted_source` | Source can provide the named fact as hard evidence when the metric is reliable and sample-size thresholds pass. | May support hard claims for registered facts only. |
| `medium_source` | Source is accepted but may depend on user/export quality, parser coverage or partial fields. | May support hard claims only when the metric is not weak, samples pass and the limitation is visible. |
| `coverage_limited_source` | Source can be strong for some captured events but has known coverage gaps. | Hard claims only for explicitly captured facts with coverage evidence; otherwise warning/context only. |
| `low_source` | Source is weak, ambiguous or incomplete for the requested fact. | Display or warning context only. |
| `unavailable_source` | Source is not integrated, not accepted or not reliable for the fact. | Suppressed from diagnosis, recommendation and AI hard evidence. |

### Current Source Registry

| Source | Current trust | Accepted facts | Not accepted / caveats |
|---|---|---|---|
| CSV import | `medium_source` for explicit match totals; `low_source` for inferred event concepts. | Source-provided match rows, result, score, map label when present, kills, deaths and other explicit uploaded totals. | User/export quality is not independently verified. Do not infer round events, side, economy, positioning, clutch, trade or exact playlist/mode. Date precision depends on the uploaded field and must be caveated unless exact source is known. |
| JSON import | `medium_source` for explicit structured totals; `low_source` for inferred event concepts. | Structured match rows and explicit fields provided by the import payload. | Same boundaries as CSV. The presence of structured JSON does not make unsupported fields reliable. |
| Demo parser | `coverage_limited_source`; may be `trusted_source` or `medium_source` for specific parser-captured facts when Metric Truth allows it. | Parser-captured round count, player events, damage, utility/flash events, opening-duel facts and timing facts when the artifact contains the required anchors. | Parser coverage gaps remain binding. Side, trade, clutch, economy and positioning are not accepted for hard advice unless a future parser-hardening task upgrades them. `early_deaths` requires timing anchors and must not fallback to `entry_deaths`. |
| Steam / Valve share-code import | `trusted_source` for Steam GC `match_time` where present and accepted match identity/date facts; `medium_source` for generic Valve matchmaking provenance and imported totals. | Exact date source `steam_gc_match_time` when present, imported match identity/provenance, result/score/totals where persisted by the accepted import path. | `Valve Matchmaking` is provenance, not exact playlist. Do not claim Premier, Competitive, Wingman, Casual, Deathmatch, FACEIT or custom mode from current Steam data. Demo header time and file modified time are not exact Steam match dates. |
| FACEIT | `unavailable_source` until an explicit FACEIT integration/source task is accepted. | None for current hard advice. | Do not label matches, filters, comparisons or recommendations as FACEIT-backed unless future reliable metadata and source policy are accepted. |

Future sources default to `unavailable_source` until added to this registry.

### Sample-Size Thresholds

Thresholds control whether a metric may be used for hard diagnosis,
recommendation or period comparison. They do not upgrade `warn`, `low` or
`unavailable` Metric Truth decisions into hard evidence.

| Metric category | Examples | Minimum for hard diagnosis/recommendation | Minimum for period comparison | Insufficient-sample behavior |
|---|---|---|---|---|
| Single-match facts | One match result, score, kills/deaths for a match. | One accepted source row may be displayed or used as evidence for that match only. | Not applicable as a trend. | Do not describe as a pattern. |
| Match-window outcome metrics | `winrate`, result counts, average round differential. | At least 10 matches in the window. | At least 10 matches in each compared window. | Show raw counts or caveated context; suppress hard trend/advice. |
| Core volume/rate metrics | Kills, deaths, `kd_ratio`, `adr`. | At least 10 matches or 120 accepted rounds, and source coverage for the metric. | Same threshold in each window. | Show the value with sample caveat; do not assign hard cause. |
| Event/opportunity metrics | `entry_kills`, `entry_deaths`, utility damage, flash impact. | At least 8 matches and 20 accepted opportunities/events for the metric. | Same opportunity threshold in each window. | Show counts only or warning context; suppress hard rate comparison. |
| Approximate/warning metrics | `kast`, `hltv_rating`, `swing_score`, `early_deaths`, `headshot_rate` where usage is `warn`. | No sample size can make these hard evidence under current Metric Truth. | Compare only as caveated context when both windows meet the relevant category sample floor. | Keep warning semantics; do not use as sole recommendation basis. |
| Low-confidence metrics | `trade_kills`, `accuracy`, `side_split_metrics`. | Not allowed for hard diagnosis/recommendation. | Suppressed from hard comparison. | Display-only or warning context according to Metric Truth. |
| Unavailable metrics/models | `traded_deaths`, `grenade_rating`, `aim_rating`, `crosshair_placement`, economy, positioning, clutch. | Not allowed. | Not allowed. | Suppress and state the model or metric is unavailable when relevant. |

If a window mixes sources, the sample count must be reported or carried with
source coverage. A source with missing values contributes only to metrics it
actually supports; it must not inflate denominators for unsupported metrics.

### Aggregation Rules

- Aggregate counts by summing accepted numerator/count fields only.
- Aggregate rates from their underlying numerator and denominator. Do not
  average percentages, ratings or ratios across matches unless the metric's
  formula explicitly defines that behavior.
- Aggregate `kd_ratio` from total kills divided by total deaths, with the
  zero-death case handled as a caveated display value rather than an infinite
  hard signal.
- Aggregate `adr` from total accepted damage divided by total accepted rounds.
- Keep source coverage with every aggregate: contributing matches, contributing
  rounds or contributing opportunities, plus omitted/missing counts when known.
- Do not impute missing metric values from adjacent stats or other sources.
- Do not merge conflicting values into one hard fact. Prefer the registered
  authoritative source for that fact; otherwise suppress or caveat the
  aggregate until conflict resolution is accepted.
- Mixed-source aggregates inherit the weakest relevant source trust tier and
  the weakest Metric Truth usage decision among values used for the claim.
- `warn`, `low`, `suppressed` and `unavailable` metrics remain bounded by their
  Metric Truth usage even when mixed with trusted metrics.
- Suppressed or unavailable values must not appear in diagnosis,
  recommendation, AI evidence arrays or hard comparison claims.
- Playlist/mode, side, map, economy, positioning, clutch and trade gaps must
  not be filled by aggregate math.

### Period Comparison Semantics

Period comparisons are non-overlapping comparisons over explicitly selected
windows. A comparison may be by date range or by equal match count, but the
window definition must be visible to the consumer when the comparison is used
for advice.

Default comparison policy:

- If a user or route selects explicit dates, compare only matches whose accepted
  played date falls inside those dates.
- If no explicit dates are selected, compare the latest complete analysis
  window with the immediately preceding non-overlapping window of the same
  match count where enough samples exist.
- Do not compare an open partial window against a complete historical window as
  a hard trend unless the partial-window caveat is visible.
- Each compared window must meet the category sample threshold independently.
- Both windows must use compatible source trust for the compared metric. If one
  window relies on `trusted_source` facts and the other relies on
  `medium_source` or `coverage_limited_source` facts, the comparison is
  caveated; if either side is `low_source` or unavailable for the fact, the
  hard comparison is suppressed.
- Freshness and recency claims require exact accepted date sources. Steam GC
  `match_time` / `steam_gc_match_time` is exact where present. Demo header time,
  file modified time or unknown uploaded dates must be caveated or excluded
  from freshness claims.
- Missing values are excluded from that metric's numerator and denominator, but
  the comparison must disclose or carry coverage. If missingness changes the
  interpretation, suppress the hard trend.
- Small deltas near zero should be presented as stable/no clear change unless
  the metric category has enough sample size and the difference is meaningful
  under the accepted metric policy.

Suppress or caveat a comparison when:

- either window fails the relevant sample threshold;
- source trust differs enough to change interpretation;
- the metric is `warn`, `low`, `suppressed` or `unavailable` for hard use;
- date precision is approximate for a freshness or recency claim;
- playlist/mode, side, map, economy, positioning, clutch or trade semantics
  would be implied beyond accepted domain boundaries;
- numerator/denominator coverage is missing, contradictory or too sparse.

## Current Integration

- Recommendation evaluation consumes Metric Truth Layer for hard-signal checks.
- Survival recommendations no longer treat `early_deaths` as a hard success/failure signal.
- AI payload includes selected metric definitions and suppressed metric lists.
- Stage 8 AI Output Validator rejects unknown/suppressed/unavailable metric ids in structured AI output and requires caveats for approximate/warn metrics.
- Diagnosis registry is still future work; existing rule-based diagnosis remains partial and must not be treated as final planner logic.

## Next Work

- Parser hardening for KAST/trade, traded deaths, side switching and utility attribution.
- Diagnosis registry from verified problems.
- Recommendation planner that chooses one primary recommendation from verified evidence.
- Prompt/version tracking and deeper AI/provider structured response hardening after Stage 8 validator.
