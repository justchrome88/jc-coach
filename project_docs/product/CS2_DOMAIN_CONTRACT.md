> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/CS2_DOMAIN_CONTRACT.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# CS2 Domain Contract

Last updated: 2026-07-08.

## Purpose

This document is the current docs/design contract for CS2 domain boundaries in
JC Coach. It is conservative by design: it describes what the app may claim
from current persisted facts and which CS2 concepts must remain unavailable,
display-only or caveated until parser/source hardening explicitly upgrades
them.

This document does not authorize product logic changes, DB/schema changes,
production DB mutation, import/parser/evaluator jobs, live Steam/Valve work,
service/deploy changes, package installation, import cap changes or major CS2
feature unlocks. `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO` until the
foundation readiness gate passes.

## Match And Round Domain Map

Current accepted domain objects:

| Object | Current meaning | Accepted use | Boundary |
|---|---|---|---|
| Match | One persisted player match row plus optional parser/import artifacts. | Overall match result, score, map label when present, player stat summary, recommendation/evaluation evidence when metric confidence allows it. | Match playlist/mode is not exact in `v0.9`; do not claim Premier, Competitive, Wingman, Casual, Deathmatch, FACEIT or custom unless future reliable metadata is captured. |
| Round | Parser-derived round context when parser artifacts exist. | Round count, round score, selected player events and timing facts when the parser captured them. | Round-level facts must not be inferred from match totals when parser round data is missing. |
| Side | T/CT attribution from current side split fields. | Display-only context with low-confidence caveat. | Side metrics must not drive diagnosis, recommendation scoring or hard AI claims until side/team-switching confidence improves. |
| Map | Source-provided or parser/import-provided map label. | Display, grouping and filtering only when a map label is present. | Map label presence is not the same as accepted map pool validation or map-specific coaching certainty. |
| Economy | Buy type, equipment value, save/force/eco/full-buy and money-state model. | Unavailable. | Do not diagnose economy decisions or recommend buy strategy from current data. |
| Positioning | Player location, pathing, angle, spacing, crosshair placement and heatmap model. | Unavailable. | Do not diagnose positioning, rotations, spacing, angle discipline or crosshair placement from current data. |
| Clutch | End-of-round low-player-count state such as 1vX or Xv1. | Unavailable as an accepted model. | Do not claim clutch win rate, clutch conversion, clutch mistakes or clutch recommendations until parser-backed semantics are accepted. |
| Trade | Trade kill/death semantics and traded/untraded death rate. | Current trade facts are weak context only. | Hard trade recommendations are blocked before parser hardening. |

## Source And Mode Limits

Accepted source labels must describe provenance and confidence, not unsupported
playlist certainty.

- Source trust, mixed-source aggregation, sample-size thresholds and period
  comparison semantics are governed by `project_docs/metrics/METRICS.md`. CS2 domain claims may
  not exceed both the source-trust policy and the per-metric Metric Truth usage
  decision.
- `mode_unknown` is the accepted playlist/mode stance for current `v0.9`
  rows unless future metadata proves otherwise.
- `provenance_demo` may identify parser/import provenance, not playlist.
- `provenance_valve_matchmaking` may identify Valve share-code provenance, not
  Premier/Competitive/Wingman/Casual/Deathmatch specificity.
- `exact_date_source=steam_gc_match_time` is accepted for exact Steam GC match
  time where present.
- Demo header time or file modified time must not be treated as exact Steam
  match date for freshness, diagnosis windows or coach claims.
- Current map labels can be shown as provided by source/parser/import, but map
  names are not yet backed by a canonical registry.

## Unavailable Models

The following models are explicitly unavailable for hard advice:

| Model | Status | Required behavior |
|---|---|---|
| Economy model | Unavailable. | Suppress hard economy diagnosis and recommendations. |
| Positioning model | Unavailable. | Suppress hard positioning, heatmap, rotation, spacing and crosshair-placement claims. |
| Clutch model | Unavailable. | Suppress clutch win-rate, clutch conversion and clutch-mistake claims. |
| Map registry | Planned, not accepted. | Treat map strings as source-provided labels until a registry is accepted. |
| Side confidence model | Low confidence. | Keep side split metrics display-only. |
| Trade model | Not hardened. | Block hard trade recommendations and traded/untraded-death claims. |

## Metric Usage Boundaries

`project_docs/metrics/METRICS.md` remains the canonical Metric Truth contract and runtime
registry source. It also defines the accepted source trust registry, sample-size
thresholds, aggregation rules and period comparison semantics for mixed sources.
This domain contract adds CS2-specific boundaries:

- Side metrics stay display-only and warning-labeled until parser confidence
  improves.
- `trade_kills` and KAST trade components may appear only as caveated context
  under current reliability rules.
- `traded_deaths` remains unavailable and suppressed.
- `crosshair_placement` remains unavailable and suppressed.
- `early_deaths` must use accepted parser timing anchors; it must not fallback
  to entry deaths.
- Economy, positioning and clutch metrics must not be invented from adjacent
  facts such as score, kills, deaths, ADR, KAST, entry kills or round count.
- Hard advice from mixed CSV, JSON, demo, Steam or future FACEIT data requires
  a registered source trust tier, enough samples for the metric category and
  compatible period comparison windows.

## Coach Output Visibility Contract

Coach-facing output includes the `/coach` page, generated reports, AI handoff
payloads, AI-generated results, recommendation summaries and API responses that
feed those surfaces.

Coach output must keep source limitations visible when advice uses weak,
approximate, low-confidence or source-limited facts:

- Show or carry the data/source limitation next to the claim, not only in
  internal docs.
- Use cautious wording for warning metrics: context, signal, possible pattern
  or needs review.
- Do not present unavailable models as missing minor details; state that the
  model is unavailable when the concept would otherwise affect advice.
- Do not convert side, trade, map, mode, economy, positioning or clutch gaps
  into hard recommendations.
- Hard trade recommendations remain blocked before parser hardening.
- Playlist/mode limitations must remain visible anywhere mode-specific advice
  would otherwise be implied.

## CS2 Glossary

| Term | JC Coach meaning |
|---|---|
| Match | Persisted player match row with source/import provenance and optional parser artifacts. |
| Round | Parser-derived round segment; accepted only when round data exists. |
| T side | Terrorist-side context; currently low-confidence for side split metrics. |
| CT side | Counter-Terrorist-side context; currently low-confidence for side split metrics. |
| Map | Source-provided map label; display/grouping label until canonical registry exists. |
| Playlist/mode | Competitive mode category such as Premier, Competitive, Wingman, Casual, Deathmatch, FACEIT or custom; currently unknown for `v0.9` hard claims. |
| Economy | Money/equipment/buy-state model; unavailable. |
| Positioning | Location, pathing, spacing, rotations, angles, crosshair placement and heatmap-style inference; unavailable. |
| Clutch | Low-player-count end-round scenario such as 1vX; unavailable as an accepted model. |
| Trade | Short-window teammate response after a kill/death; not hardened for hard recommendations. |
| KAST | Kill, assist, survive or trade participation; approximate because the trade component is not fully reliable. |
| Entry duel | Opening kill/death context from parser/source ordering; usable only within Metric Truth reliability limits. |
| Utility | Grenade/flash damage and effect context; available only where parser/source support and Metric Truth allow it. |
| Source limitation | A visible caveat describing source, parser coverage, confidence or unavailable model boundaries behind a claim. |

## Canonical Map Registry Plan

A future map registry may be accepted only through an explicit scoped task. The
registry should define:

- canonical map IDs, display names and aliases;
- active, legacy, workshop/custom and unknown classifications;
- source normalization rules for parser/import/Steam labels;
- behavior for unknown or unsupported map strings;
- tests or fixtures proving normalization behavior;
- a migration/backfill decision if persisted map values need normalization.

Until that plan is implemented and accepted, current map strings remain
source-provided labels. Do not treat a label as validated map-pool membership
or map-specific coaching evidence by itself.

## Future Upgrade Criteria

Any upgrade from unavailable/display-only/caveated to hard advice requires a
separate accepted task with evidence, tests or fixtures appropriate to the
domain:

- parser hardening for side switching, trade windows, traded deaths, clutch
  states, economy and positioning;
- source trust and sample-size thresholds for mixed source data;
- confidence labels that reach coach output;
- semantic AI/eval checks for overclaiming and unsupported metrics;
- explicit product decision if a concept remains intentionally out of scope.
