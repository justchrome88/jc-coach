# WP-015B Metrics Correctness Diagnosis

Date: 2026-07-04

## RESULT: DIAGNOSED

WP-015B diagnosed the current metric layer for `v0.7` Metrics Correctness. This pass was read-only except for creating this audit report. No code, tests, schema, production DB rows, live Steam/import/parser jobs, parser reruns, downloads or demo files were changed.

## Product Version Observed

`v0.6`

Observed from current status, handoff, project control, roadmap and WP-014F promotion docs. WP-015A1 has already reconciled match-date truth enough for metrics work to start.

## DB SHA

```text
8811b08c3e15348ab60ee022887c90ecbe4a17b4bef8ea5d035c083d8f2b6f1c  data/cs2_coach.db
```

## Metrics Inventory

Current metric users:

| Surface | Code path | Metrics shown/used | Current safety |
|---|---|---|---|
| Dashboard | `app/web/routes.py:/dashboard`, `app/templates/dashboard.html` | matches, winrate, K/D, ADR, KAST, rating, swing, form score, data-quality coverage, ADR profile, recent-vs-previous session, map stats, recent match table | Excludes `steam_history`, but recent windows use `played_at` without exact-date gate; KAST/swing shown without strong confidence labels. |
| Stats | `app/web/routes.py:/stats`, `app/templates/stats.html` | all dashboard metrics plus rounds, round diff, entry kills/deaths, utility damage, flash assists, HS%, aim profile, weapon table | Same date/window risk; aim confidence exists but may say high from coverage while underlying metrics still have known parser limitations. |
| Matches list | `app/web/routes.py:/matches`, `app/templates/matches.html` | date, exact/approx badge, map/result/source, K/D, ADR, KAST, swing, rating, entry, utility | Best current date-truth UI; labels exact/approx/unknown per row. Sorting/filtering still uses `Match.played_at` even for approximate rows. |
| Match detail | `app/web/routes.py:/matches/{id}`, `app/templates/match_detail.html` | combat, opening, utility, sides, aim profile, parser evidence, parser artifact counts, weapons, duels, grenades, date truth | Strongest per-match evidence view; parser confidence is visible here but not promoted to aggregate confidence decisions. |
| Rule report | `app/services/report_generator.py`, `/report/generate` | summary, period comparison, map stats, weaknesses, coach focus, active recommendation progress | Writes reports when explicitly requested; uses recent windows by `played_at` and does not include date/artifact confidence in report text. |
| Coach page | `app/web/routes.py:/coach`, `coach_rules.py`, `mistake_detection.py`, `recommendation_tracking.py`, `app/templates/coach.html` | current tracked recommendation, latest match, weak metric notes, aim profile, structured mistakes, category scorecard, recommendation progress | Metric Truth warnings exist, but summary/mistake detection still makes some hard-looking claims from approximate metrics. |
| Recommendation tracking | `app/services/recommendation_tracking.py` | baseline/current: K/D, entry deaths, early deaths, KAST, ADR, utility damage, flash assists, winrate; per-match evaluation signals | Uses Metric Truth for hard-claim checks in evaluations, but baselines are still built from latest matches without exact-date or sample-quality gating. |
| AI payload | `app/services/ai_coach.py` | summary, dashboard status, aim profile, period comparison, map stats, weaknesses, structured mistakes, metric truth registry, recent matches | Payload includes Metric Truth definitions/suppressed lists; source metrics still include aggregate outputs that may already mix approximate dates/confidence. |

All primary query paths use `playable_match_select()`, which excludes `source="steam_history"`. That prevents placeholder rows from entering dashboard/stats/coach/report/AI metric sets.

## Metric Formula Inventory

| Metric | Formula / field source | Tables/fields | Parser artifacts required | Window/date dependency | Current classification |
|---|---|---|---|---|---|
| Match count | count playable `Match` rows | `matches.source` | none | date only for recent/date filters | trusted |
| Winrate/result | wins / matches where `result=="win"` | `matches.result` | score/result source; parser score is best-effort but present | recent/map/date windows depend on ordering | trusted for display, partial for parser-derived result validation |
| Round score/diff | sum `rounds_for`/`rounds_against` | `matches.rounds_for`, `rounds_against` | `demo_rounds`, parser score inference | no for all-time; yes for windows | trusted when score confidence high; current parser says score high for production rows |
| K/D | average `Match.kd`; importer computes kills / deaths or 1 if zero deaths | `kills`, `deaths`, `kd` | `demo_duels`/death events for parsed demos | no except windows | trusted if target player is correct; need death-zero fixture |
| ADR | average `Match.adr`; parser computes damage / rounds | `adr`, damage/rounds | `demo_damage_events`, `demo_rounds` | no except windows | medium; production parser confidence says ADR high for all playable rows |
| KAST | average `Match.kast` | `kast`, player-round facts | `demo_player_rounds`, death/assist/survival/trade proxy | no except windows | partial/approximate; trade component is explicitly low |
| Rating | average `Match.rating` | `rating` | source-provided only | no except windows | unsafe/unavailable in production: 0/19 playable rows have rating |
| Swing score | average `Match.swing_score`; parser heuristic | `swing_score`, raw swing payload | deaths, damage, round end, bomb events | no except windows | partial/approximate |
| Form score | weighted result, K/D, ADR, KAST, rating, swing over latest 15 | `result`, `kd`, `adr`, `kast`, `rating`, `swing_score` | mixed | yes, latest 15 by `played_at` | unsafe until exact-date and component confidence gates exist |
| Entry kills/deaths/diff | sums `entry_kills`/`entry_deaths`; opening duel facts | `entry_kills`, `entry_deaths` | `demo_duels`, death event order | no except windows | partial/medium |
| Early deaths | `early_deaths` timing-window fact | `early_deaths` | death events plus round timing anchors | no except windows | partial/approximate; low for rows `21-24,37-38`, medium for rows `25-36,70` |
| Utility damage | average/sum `utility_damage` | `utility_damage` | damage events with grenade attribution | no except windows | partial/medium |
| Flash assists | average/sum `flash_assists` | `flash_assists` | blind/kill correlation | no except windows | partial/approximate |
| Enemies flashed | per-match/detail field | `enemies_flashed` | blind events | no except windows | partial/approximate |
| Headshot percent | average `headshot_percent` | `headshot_percent`, weapon stats | `demo_weapon_stats`, death events | no except windows | partial/medium |
| Weapon breakdown/top weapons | aggregate raw `weapon_breakdown` | `matches.raw_json`, `demo_weapon_stats` | weapon stats, weapon fire/hurt correlation | no except windows | partial; accuracy remains low |
| Opening duel success | entry kills / (entry kills + entry deaths) | `entry_kills`, `entry_deaths` | death event order | no except windows | partial/medium |
| Multi-kill rounds | raw `aim_summary.multi_kill_rounds` sum | `matches.raw_json` | death events per round | no except windows | partial; not in Metric Truth registry as standalone |
| Map stats | per-map summary | `map_name` plus summary metrics | mixed | no unless map trend added | partial; sample sizes are currently small for most maps |
| Side winrate | T/CT side won/lost fields | side fields | reliable side/team inference | no except windows | unsafe/unavailable in production: 0/19 side fields present |
| Crosshair placement | not implemented | none | view angles/position timeline | n/a | unavailable |
| Grenade rating / aim rating | product concepts only | none | stable formulas absent | n/a | unavailable |
| Recommendation evaluation | compares per-match evidence to baseline | recommendation tables plus match metrics | mixed | baseline/latest depends on match ordering | partial; Metric Truth protects some hard claims but baseline quality is not gated |

## Parser Artifact Coverage

Production playable rows: `19` (`matches.source="demo"`). `steam_history` placeholders: `51`.

Every playable demo row has a `demo_parse_artifacts` row and normalized parser artifacts:

| Table | Total rows | Covered playable match ids |
|---|---:|---|
| `demo_parse_artifacts` | 19 | `21-38, 70` |
| `demo_rounds` | 406 | `21-38, 70` |
| `demo_player_rounds` | 4083 | `21-38, 70` |
| `demo_weapon_stats` | 4744 | `21-38, 70` |
| `demo_damage_events` | 11992 | `21-38, 70` |
| `demo_duels` | 2848 | `21-38, 70` |
| `demo_grenade_events` | 3445 | `21-38, 70` |

Playable demo rows with missing artifacts: none.

Production metric field coverage for playable rows:

| Field | Present |
|---|---:|
| `result`, score, kills, deaths, assists, K/D, ADR, KAST, swing, HS%, entry kills/deaths, early deaths, utility damage, enemies flashed | 19/19 |
| `rating` | 0/19 |
| T/CT side fields | 0/19 |

Parser confidence in production:

- Overall `parser_confidence=medium` for all 19 playable rows.
- Kills/deaths/assists: high.
- ADR: high.
- Entry duels: medium.
- KAST: medium, with `kast_trade_component=low`.
- Utility: medium.
- Weapon accuracy: medium.
- Side stats: low for all rows.
- Traded deaths: unavailable where present.
- Early deaths: low for rows `21-24,37-38`, medium for rows `25-36,70`.

## Date-Dependent Metrics

Date/order-dependent paths:

- Dashboard recent 10, recent 15, previous 15, chart series.
- Stats `last N`, date range filters, recent table and chart series.
- `compare_periods()` current/previous windows.
- `calculate_form_score()` latest 15.
- `detect_structured_mistakes()` latest 15 match-level mistakes.
- Coach latest match and evaluated recent matches.
- Report period start/end and period comparison.
- AI payload recent matches and period comparison.
- Recommendation baseline/latest ordering.
- Match list date sort and date filters.

Current protection:

- `steam_history` placeholders are excluded.
- Match list/detail show date truth labels.
- WP-015A1 left playable date state at 17 exact, 2 approximate, 0 unknown.

Current gap:

- Aggregate date windows do not require `raw_json.match_date_status=exact_match_date_available` and `match_date_source=steam_gc_match_time`.
- Rows `37-38` can still be included in recent windows, trend comparisons and recommendation baselines as if their date were exact.

## Unsafe Metrics

High-risk or misleading today:

- `form_score`: mixes result/KD/ADR/KAST/rating/swing and is displayed as one precise score without component confidence; also depends on latest 15 ordering.
- `rating`: displayed on dashboard/stats/matches/detail even though production playable coverage is 0/19; current output is mostly `n/a`, but report text still names rating as a control metric.
- `KAST`: shown as ordinary aggregate while registry marks it approximate and parser warns the trade component is incomplete.
- `swing_score`: shown as ordinary aggregate while registry marks it approximate.
- `early_deaths`: used in structured mistakes/recommendation context; registry warning exists, but broad mistake text can still sound definitive.
- `flash_assists` and `enemies_flashed`: approximate blind/kill correlation and context-light flash counts.
- `utility_damage`: medium confidence, but current aggregate labels do not distinguish grenade attribution limits.
- `side_split_metrics`: no production coverage and registry suppresses hard use; match detail still shows side table as `n/a`.
- `map stats`: small samples are shown/ranked; e.g. several maps have 1-2 matches and can be presented as best/weak maps.
- `ADR profile confidence`: can show `high` from field coverage alone, not from source/date/artifact confidence or sample representativeness.
- `data_quality.label`: reports high because fields are populated, but does not account for metric reliability, exact-date truth, parser confidence or sample size.
- Recommendation baselines: built from latest matches by `played_at` without exact-date/date-window or artifact-confidence filtering.
- AI payload: includes Metric Truth definitions, but also includes precomputed weaknesses and summaries that may already contain approximate metrics.

## Trusted/Partial/Unsafe Classification

Safe enough for v0.7 with labels:

- Trusted: match count, result/winrate, total score/round diff, kills, deaths, K/D, assists with medium caveat.
- Partial/medium: ADR, headshot percent, entry kills/deaths, utility damage, weapon breakdown/top weapons, map stats with sample-size labels.
- Approximate: KAST, swing score, early deaths, flash assists, enemies flashed, form score.
- Low/suppressed: trade kills, side split metrics, accuracy as hard evidence.
- Unavailable/suppressed: traded deaths, grenade rating, aim rating, crosshair placement, rating as local trusted metric.

Production-specific classification:

- All-time aggregates over playable rows are safer than trend windows because they do not depend on exact chronological ordering.
- Exact-date recent windows can use rows `21-36,70`.
- Approximate rows `37-38` should be excluded from exact recent/trend/freshness windows or included only with an explicit approximate-window label.
- No DB reset is needed; no parser rerun is needed for this diagnosis.

## UI/Coach/Recommendation Risk

UI risk:

- Dashboard/stats show confidence-like labels that currently measure field coverage more than metric truth.
- Only matches/match detail expose date truth clearly.
- Aggregate pages need visible badges for exact-date window count, approximate rows excluded/included, sample size and weak metrics.

Coach risk:

- `detect_weaknesses()` and `mistake_detection.py` can produce strong claims from KAST, utility, entry and map stats without enforcing Metric Truth at the point of claim.
- Crosshair placement is handled correctly as no-data in `mistake_detection.py`.

Recommendation risk:

- Evaluation checks call `is_metric_allowed_for_hard_claim()` for some comparisons, which is good.
- Baselines and target metrics can still be created from low sample sizes and approximate-date windows.
- `early_deaths` appears in targets/evidence as warning, but UI must keep it visibly non-hard.

AI risk:

- `build_ai_coach_payload()` includes metric truth metadata and prompt rules, but also includes already-computed summaries, weaknesses and focus. If those upstream computations are not gated, AI receives unsafe claims as facts.

## Required Metric Confidence Model

Recommended model for WP-015 repair:

| Level | Meaning | Requirements |
|---|---|---|
| `exact` | Safe for hard metric claims and trend windows. | Playable row; exact date when windowed; source field present; parser/source confidence high or trusted; sample size threshold met. |
| `partial` | Usable with caveat; not sole hard recommendation evidence. | Field present; parser confidence medium or registry medium; sample size disclosed. |
| `low_confidence` | Display only with warning or use as secondary context. | Approximate registry metric, low parser confidence, small sample, or incomplete artifact component. |
| `unavailable` | Suppressed from claims. | Missing field/artifact, registry unavailable/suppressed, or known formula absent. |

Minimum sample recommendations:

- All-time summary: show count always, but label confidence below 5 matches.
- Recent/trend windows: require at least 5 exact-date matches for a low-confidence trend, 10 for partial, 15 for normal display.
- Map stats: require 3 matches for partial map claim, 5 for stronger map recommendation.
- Recommendation baseline: require 10 playable matches; exact-date baseline preferred for time-based categories; otherwise mark baseline partial.
- Parser artifact metrics: require artifact row plus relevant artifact counts and parser metric confidence at least medium.

Date requirements:

- Recent N, previous N, form score, trend, report period and recommendation baseline must either use exact-date rows only or expose `approximate_dates_included`.
- Date filters should warn when approximate rows are included.

UI requirements:

- Show metric reliability/caveat badges on dashboard/stats/coach/report, not only match detail.
- Report counts: `exact_date_matches`, `approximate_date_matches`, `excluded_from_exact_windows`.
- Do not display `rating` as a meaningful control metric while coverage is 0/19.

## Minimal v0.7 Repair Scope

Recommended WP-015C/D scope:

1. Add a metric evidence/confidence helper that combines Metric Truth registry, sample size, exact-date truth and parser confidence.
2. Add exact-date filtered window helpers for recent/trend/form/report/recommendation baseline paths.
3. Update dashboard/stats/coach/report/AI payload to include confidence metadata and approximate-date counts.
4. Suppress or relabel `rating`, side splits, grenade rating, aim rating, crosshair placement and traded deaths where unsupported.
5. Keep KAST, swing, early deaths, flash assists and utility as visible but caveated metrics.
6. Add mocked/local tests:
   - `steam_history` placeholders are excluded from playable metrics.
   - approximate-date rows are excluded or labeled in exact recent windows.
   - recent/trend windows report exact/approx counts.
   - map stats enforce sample-size labels.
   - rating 0-coverage is unavailable, not a hard report metric.
   - AI payload does not present suppressed/unavailable metrics as hard evidence.
   - recommendation baseline/evaluation carries confidence and blocks suppressed hard metrics.
   - parser artifact completeness gates parser-derived metrics.

## Deferred Metrics / Out of Scope

Defer from v0.7:

- Full HLTV 2.0 rating implementation.
- Crosshair placement from view-angle/position data.
- Traded/untraded death rate.
- Stable grenade rating and aim rating composites.
- Full side split correctness.
- Live Steam/API metadata recovery for placeholder rows.
- Parser reruns or demo cleanup.
- Recommendation planner rewrite; WP-015 should harden metric truth feeding current coach/recommendation flows.

## Whether DB Reset Is Needed

No.

Current production data is classifiable: 19 playable demo rows, complete artifact coverage for those rows, 17 exact playable dates, 2 approximate playable dates and no playable unknown dates. Metric correctness requires confidence/gating repairs, not a reset/resync.

## Production DB Touched

No. The DB was queried read-only for inventory and coverage.

## Production Files Touched

No production demo/upload/temp files were changed. This audit report was created under `docs/audit/`.

## Live Import/Parser Run

No.

## Can Proceed To Repair

Yes.

Proceed to a focused WP-015C repair for metric confidence/date-window gating and UI/payload labeling. Do not expand WP-015 into parser reruns, live imports, full recommendation planner work or storage cleanup.

## Read-Only Commands Used

Representative safe commands used:

```bash
git status --short
git log --oneline -12
df -h
du -sh data/uploads data/tmp 2>/dev/null || true
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
rg -n "get_summary|compare_periods|get_aim_profile|metric|played_at" app tests
.venv/bin/python - <<'PY'
# sqlite3 read-only style queries for matches/artifact/metric coverage
PY
```
