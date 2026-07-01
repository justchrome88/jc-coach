# Feature Roadmap Scoring

This document converts `docs/COMPETITOR_FEATURE_MATRIX.md` into an implementation roadmap.

Excel-ready Russian workbook: `docs/feature_roadmap_scoring_ru.xlsx`.

## Scoring Rules

- `Difficulty 1-10`: 1 is trivial UI/data work, 10 is infrastructure-heavy or unrealistic for this project stage.
- `Implemented %`: how much of the expected competitor-grade feature exists in our product today.
- `Popularity 1-10`: estimated user demand from competitor positioning, public discussion, and product logic.
- `Popularity basis`: `High signal` means clearly promoted by competitors and discussed by users. `Medium signal` means likely useful but less frequently requested. `Low signal` means niche, team/pro-only, or not a current MVP driver.

## Sources Used

- Scope.gg homepage: https://scope.gg/
- Scope.gg CS2 support announcement: https://blog.scope.gg/scopegg-cs2-en/
- Scope.gg guides: https://scope.gg/guides/
- Leetify homepage: https://leetify.com/
- Leetify stats glossary: https://leetify.com/blog/leetify-stats-glossary/
- Leetify blog / product updates: https://leetify.com/blog/
- Refrag wiki: https://wiki.refrag.gg/
- Refrag homepage: https://refrag.gg/
- Reddit discussion examples:
  - Leetify accuracy and progress discussion: https://www.reddit.com/r/GlobalOffensive/comments/1cnvuwb/how_accurate_is_leetify/
  - CS analytics tool comparison: https://www.reddit.com/r/LearnCSGO/comments/1ekho5s/leetify_csstats_scopegg_what_is_objectively_the/
  - Free 2D demo viewer demand: https://www.reddit.com/r/GlobalOffensive/comments/1gwwff4/is_there_any_good_free_2d_demo_viewer/
  - ESEA 2D replay / Refrag-Leetify comparison discussion: https://www.reddit.com/r/GlobalOffensive/comments/1l3xpo2/review_any_esea_match_in_2d_replay_mode/
  - CS2 demo analysis tooling demand: https://www.reddit.com/r/GlobalOffensive/comments/1jtukjy/automated_demo_analysis/

## Full Feature Scoring

| Feature | Difficulty 1-10 | Implemented % | What We Already Have | What To Add | Popularity 1-10 | Popularity Basis | Recommended Decision |
|---|---:|---:|---|---|---:|---|---|
| Match history | 2 | 65% | `/matches`, filters, core columns, DEM/CSV/JSON rows | Pagination, sorting, source badges, better match details page | 9 | High signal: every analytics product starts here | Keep improving now |
| Dashboard overview | 2 | 70% | `/` with core stats, trend chart, map table | Better visual hierarchy, session summaries, source confidence labels | 9 | High signal: Scope/Leetify front-door feature | Keep improving now |
| CSV/JSON import | 2 | 85% | Upload, API, dedupe, missing-column tolerance | Better validation report, import preview, export template | 6 | Medium signal: useful for MVP/manual import | Maintain |
| Official `.dem` upload | 7 | 45% | Real uploaded demo imports into match list | More robust parser mappings, player picker, background processing, error UX | 10 | High signal: core of Scope/Leetify-style value | Top priority |
| Server-side demo inbox | 2 | 90% | Bitvise/SFTP inbox, UI import, duplicate handling | Delete/archive buttons, import status history | 7 | High for our current workflow | Keep |
| Steam / FACEIT login | 5 | 0% | None | Auth, account linking, profile storage | 8 | High signal: Scope/Leetify use it for onboarding | Later, after DEM stability |
| Automatic match import | 8 | 0% | None | Steam/GC/share-code or FACEIT API flow, background jobs | 9 | High signal: removes manual friction | Later, high value |
| Map performance | 3 | 50% | Basic map winrate/ADR/KD table | Side stats, map-specific trends, map detail page | 8 | High signal: Scope explicitly promotes map performance | Next |
| Map-specific coach focus | 4 | 25% | Weak maps detected in report/rules | Dedicated weak-map plan, map drills, tracked goals per map | 8 | High product logic: actionable coaching | Next |
| Last period comparison | 2 | 80% | Last 15 vs previous 15 comparison | Custom periods, chart deltas, explanation text | 7 | Medium-high: progress framing is common | Maintain/improve |
| Progress tracking | 3 | 45% | Trend chart, recommendation progress | Metric-specific trend pages, weekly/monthly views | 8 | High signal: Scope promotes progress | Now |
| Active training goal | 4 | 55% | One active goal, baseline, target, score | Goal creation UI, custom goals, multiple categories | 8 | High product differentiator | Now |
| Per-match goal status | 4 | 65% | Green/yellow/red per match | Evidence details modal, filters by status | 7 | High for our coach loop | Now |
| Coach report | 4 | 55% | Rule-based markdown/html report | Better sections, source confidence, DEM evidence, weekly report | 8 | High product logic: users want "what to do next" | Now |
| AI coach report | 5 | 0% | Aggregated payload concept only | OpenAI integration, prompt, safeguards, fallback | 8 | High signal from AI-analysis interest | Next |
| Recommendation lifecycle | 5 | 10% | Active status exists in DB | Complete/pause/extend/archive UI and history | 7 | Medium-high: needed once goals matter | Next |
| Aim stats | 8 | 10% | HS%, K/D, partial weapon events available | Accuracy, time-to-damage, crosshair placement, spray metrics | 9 | High signal: Leetify/Refrag discussions often center aim | Later, hard |
| First duels | 5 | 45% | Entry kills/deaths from first death per round | Side/map context, first contact timing, trade context | 8 | High signal: directly actionable | Next |
| Early deaths | 7 | 15% | Fallback to entry deaths | Round-phase death timing from freeze_end/round_start, thresholds | 8 | High for survival coaching | Next |
| KAST | 7 | 35% | Best-effort kill/assist/survive estimate | Trade detection and proper round participation | 7 | Medium-high: common stat, but less user-requested than ADR/KD | Next |
| ADR | 4 | 75% | Works from DEM `player_hurt` and CSV/JSON | Damage validation, team damage exclusions, round count confidence | 9 | High signal: universal CS stat | Maintain |
| Utility damage | 5 | 30% | Basic weapon-name based utility damage | Better grenade owner tracking, molotov/incendiary attribution | 8 | High signal: Scope/Leetify utility discussions | Next |
| Flash assists | 5 | 25% | Basic `assistedflash` count | Player_blind joins, duration thresholds, enemy-only filter | 7 | Medium-high: useful but needs trust | Next |
| Enemies flashed | 5 | 10% | Event available, not reliable in match table | Enemy/team filter, duration aggregation, per-round context | 7 | Medium-high: utility users care | Next |
| Grenade effectiveness | 8 | 0% | None beyond raw utility damage | Define usefulness rules, lineups, round outcome relation | 7 | Medium-high, but hard to make accurate | Later |
| Grenade lineups library | 5 | 0% | None | Content database, map UI, screenshots/videos | 7 | Medium-high: Scope app/Refrag Utility Hub signal | Later |
| Interactive utility hub | 9 | 0% | None | Interactive map, lineup playback, practice states | 6 | Medium: valuable but content/product-heavy | Much later |
| Clutch stats | 7 | 0% | None | Alive-player state by round, clutch attempt detection | 7 | Medium-high: common analytics feature | Later |
| Economy analytics | 8 | 0% | None | Equipment/money parsing, buy classification, outcome model | 6 | Medium: valuable, less casual-visible | Later |
| Side stats | 5 | 20% | Score by side partially inferred | Per-side player stats, side switching, T/CT performance UI | 8 | High: map/side weakness is actionable | Next |
| Round-by-round timeline | 7 | 0% | Raw round events can be parsed | Round table, key events, player contribution per round | 7 | Medium-high: helpful for review | Later |
| Mistake detection | 8 | 25% | Basic rule-based weakness detection | Evidence-backed mistake labels, confidence, examples | 9 | High: users explicitly seek mistake correction | Iterative now |
| Heat maps | 9 | 0% | Coordinates exist in some events | Map coordinate transforms, zone rendering, UI | 7 | Medium-high: flashy and useful, but hard | Later |
| Position/callout analysis | 9 | 0% | Last place fields may be available | Map zones, callout mapping, death cluster logic | 8 | High for coach value, very hard | Later |
| 2D demo viewer | 10 | 0% | None | Tick positions, map renderer, playback UI | 8 | High signal: Scope/Refrag/Leetify pro discussions | Much later |
| Automatic highlights/clips | 10 | 0% | None | Video/demo rendering, highlight detection, storage | 7 | Medium-high, but infra-heavy | Much later |
| Shareable match reports | 4 | 0% | None | Public/private URLs, report IDs, access controls | 5 | Medium: useful after multi-user | Later |
| Friend comparison | 6 | 0% | None | Users, profiles, friend graph, comparison UI | 6 | Medium: Leetify social angle | Later |
| Team contribution / carry detection | 8 | 0% | None | Teamwide stats, impact model, round context | 7 | Medium-high: Leetify report value | Later |
| Rank benchmark comparison | 9 | 0% | None | Large benchmark dataset or external source | 8 | High user interest, but data-blocked | Not now |
| Public data library | 10 | 0% | None | Massive user base and aggregation pipeline | 5 | Medium product value, impossible now | Never for MVP |
| Post-match journal | 5 | 0% | None | Manual tags, correlation over sessions | 5 | Medium: Leetify product update signal | Later |
| Training routines | 5 | 20% | 7-day plan in report | Routine UI, checklist, reminders, goal linkage | 8 | High: users need concrete practice | Next |
| Aim training modes | 10 | 0% | None | CS2 server/workshop/training infra | 8 | High in Refrag audience | Much later |
| Hosted CS2 practice servers | 10 | 0% | None | Server orchestration, maps, billing, anti-abuse | 6 | Medium-high but outside current product | Not now |
| Bootcamp mode | 9 | 0% | None | Multi-step training product and tracking | 6 | Medium: Refrag-specific value | Much later |
| Academy videos | 4 | 0% | None | Content pages, curation, video embedding | 5 | Medium-low unless we create content | Later |
| Strategy board | 6 | 0% | None | Map canvas, drawing tools, saved tactics | 5 | Medium, more team-focused | Later |
| Team/scrim tools | 8 | 0% | None | Teams, roles, shared notes, scrim review | 5 | Medium, not personal MVP | Later |

## Already Implemented Feature Table

| Implemented Feature | Current Completion % | User Value | Gaps / Next Work | Related Competitor Feature |
|---|---:|---|---|---|
| FastAPI web app | 80% | Product runs as a real web panel | Deployment hardening, auth later | Foundation |
| SQLite + SQLAlchemy match storage | 75% | Persistent personal match database | Migrations/Alembic, PostgreSQL later | Foundation |
| CSV import | 85% | Fast manual data upload | Import preview and validation details | Match history |
| JSON import | 80% | Script/export-friendly upload | Schema docs, validation details | Match history |
| Duplicate protection | 80% | Prevents repeated imports | Better duplicate UI messaging | Match history |
| Official DEM import | 45% | Real CS2 demo can become match stats | Stronger event mapping, parser confidence, background jobs | Scope/Leetify demo analysis |
| Bitvise/SFTP demo inbox | 90% | User can upload large demos outside browser | Archive/delete UI | Internal usability |
| Match list page | 65% | See imported games in one place | Sorting, pagination, detail page | Match history |
| Match filters | 55% | Filter by map/result/date | More filters: source, coach status, imported date | Match history |
| General stats dashboard | 70% | Quick overview of performance | Better charts, sessions, explanatory labels | Dashboard overview |
| Trend chart | 45% | Visual progress over recent games | More metric toggles and time ranges | Progress tracking |
| Map stats | 50% | Shows best/worst maps | Map detail page, side splits | Map performance |
| Last 15 vs previous 15 | 80% | Shows recent form changes | Custom periods and better explanations | Progress tracking |
| Rule-based weakness detection | 25% | Gives first coach focus | Evidence examples, confidence, richer rules | Mistake detection |
| Coach report | 55% | Generates actionable written analysis | AI version, better formatting, weekly history | Coach report |
| Separate coach page | 60% | Coach info is separate from stats | Goal controls, recommendation history | Coach experience |
| Active recommendation tracking | 55% | Tracks whether advice is followed | Custom recommendations, lifecycle controls | Differentiator |
| Per-match green/yellow/red status | 65% | User sees whether match helped goal | Evidence modal, status filters | Recommendation tracking |
| DEM-based score/result inference | 45% | Imported demo has map/result/score | Validate side switching across more demos | Match details |
| DEM-based ADR/KD/KAST/entry | 45% | Real demo contributes to analysis | Better KAST/trade logic, early death timing | Core analytics |
| Report includes active recommendation | 50% | Coach report reflects current training goal | More detailed progress section | Coach report |
| README / worklog docs | 75% | Project is understandable and reproducible | Keep updated as UX changes | Developer/product docs |
| Competitor feature matrix | 80% | Gives product direction | Revisit after user testing | Product planning |

## Immediate Build Recommendation

The next best work is not adding many new shiny pages. It is making official `.dem` import trustworthy:

1. Add a demo import result screen showing selected player, score, map, key stats, and parser confidence.
2. Let the user choose player if auto-detection is wrong.
3. Add match detail page for one match.
4. Improve side stats, KAST, early deaths, utility and flash metrics from real demos.
5. Add evidence panels to the coach page so recommendations are explainable.
