> СТАТУС: ВСПОМОГАТЕЛЬНЫЙ / ЧАСТИЧНО АКТУАЛЬНЫЙ / НЕ SOURCE OF TRUTH
> Канонический источник: `docs/PROJECT_CONTROL.md` и `docs/ROADMAP.md`.
> Не использовать этот файл как текущий план реализации, если `PROJECT_CONTROL` явно на него не ссылается.

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
| Match history | 2 | 100% | `/matches`, filters, sorting, pagination, source badges, goal-status filter, match detail page | Future polish only: saved views and export | 9 | High signal: every analytics product starts here | Done for current MVP |
| Dashboard overview | 2 | 100% | `/` with core stats, trend chart, map table, data quality, ADR profile, source breakdown, recent session block | Future polish only: custom widgets | 9 | High signal: Scope/Leetify front-door feature | Done for current MVP |
| CSV/JSON import | 2 | 85% | Upload, API, dedupe, missing-column tolerance | Better validation report, import preview, export template | 6 | Medium signal: useful for MVP/manual import | Maintain |
| Official `.dem` upload | 7 | 88% | Real DEM import, duplicate handling, parser confidence, event counts, swing_score, deep normalized tables, round/player/weapon/damage/duel/grenade storage, match detail deep parser UI | Player picker before save, parsed_payload_verified status, side switching validation | 10 | High signal: core of Scope/Leetify-style value | Continue now |
| Server-side demo inbox | 2 | 90% | Bitvise/SFTP inbox, UI import, duplicate handling | Delete/archive buttons, import status history | 7 | High for our current workflow | Keep |
| Steam / FACEIT login | 5 | 60% | Steam OpenID, SteamAccount, callback, settings UI, Game Authentication Code onboarding. FACEIT remains future. | Harden OpenID verification, profile enrichment, FACEIT auth/linking | 8 | High signal: Scope/Leetify use it for onboarding | Continue after Steam hardening |
| Automatic match import | 8 | 75% | Steam share-code sync, `steam_import_all` background job, service bot GC resolver, `.dem.bz2` download, `.dem` parse/import, status overview | Production scheduler, retries/backoff, FACEIT support, richer job detail page | 9 | High signal: removes manual friction | Current top product flow |
| Demo storage lifecycle | 5 | 60% | `/settings/storage`, storage API, manifest, referenced/unreferenced/missing/suspicious classification, future delete candidates, deep parser storage contract documented | Add parsed_payload_verified status and explicit retention/delete policy | 8 | High operational value once auto-import scales | Next before raw delete |
| Map performance | 3 | 50% | Basic map winrate/ADR/KD table | Side stats, map-specific trends, map detail page | 8 | High signal: Scope explicitly promotes map performance | Next |
| Map-specific coach focus | 4 | 25% | Weak maps detected in report/rules | Dedicated weak-map plan, map drills, tracked goals per map | 8 | High product logic: actionable coaching | Next |
| Last period comparison | 2 | 80% | Last 15 vs previous 15 comparison | Custom periods, chart deltas, explanation text | 7 | Medium-high: progress framing is common | Maintain/improve |
| Progress tracking | 3 | 65% | Trend chart, multi-category recommendation progress, category summary/history | Metric-specific trend pages, weekly/monthly views | 8 | High signal: Scope promotes progress | Now |
| Active training goal | 4 | 80% | Multi-category active goals, baseline, target, score, extend/restart lifecycle actions | User-created custom goals, tuned thresholds | 8 | High product differentiator | Now |
| Per-match goal status | 4 | 75% | Green/yellow/red/gray per match and recommendation evidence | Evidence details modal, filters by all category statuses | 7 | High for our coach loop | Now |
| Coach report | 4 | 55% | Rule-based markdown/html report | Better sections, source confidence, DEM evidence, weekly report | 8 | High product logic: users want "what to do next" | Now |
| AI coach report | 5 | 75% | Provider abstraction, structured payload, Codex handoff, local_llm scaffold, saved AI report with payload snapshot/hash/history | Real model setup, structured AI sections, feedback loop/evals | 8 | High signal from AI-analysis interest | Next |
| AI provider abstraction | 4 | 75% | `codex_cli_handoff`, `local_llm`, health/generate endpoints, persistence metadata | Streaming, provider UI diagnostics, structured JSON output | 8 | High product logic: keeps AI coach independent from one model vendor | Now |
| Recommendation lifecycle | 5 | 75% | Active/paused/completed/archived, extend, restart, category summary, history UI/API | User-created goals, restart reason/comments, deeper history charts | 7 | Medium-high: needed once goals matter | Next |
| Aim stats | 8 | 75% | ADR, K/D, HS%, damage per death, opening duel success, multi-kill rounds, weapon breakdown, estimated accuracy, swing_score/jc_swing_v1, deep weapon_stats tables, data gaps | Spray/TTK/crosshair placement after reliable view-angle/position timeline; dedicated aim/impact dashboard | 9 | High signal: Leetify/Refrag discussions often center aim | Continue after parser payload |
| First duels | 5 | 55% | Entry kills/deaths and opening duel success in aim profile | Side/map context, first contact timing, trade context | 8 | High signal: directly actionable | Next |
| Early deaths | 7 | 15% | Fallback to entry deaths | Round-phase death timing from freeze_end/round_start, thresholds | 8 | High for survival coaching | Next |
| KAST | 7 | 35% | Best-effort kill/assist/survive estimate | Trade detection and proper round participation | 7 | Medium-high: common stat, but less user-requested than ADR/KD | Next |
| ADR | 4 | 100% | Works from DEM `player_hurt` and CSV/JSON, dashboard ADR profile, coverage/confidence, recent delta, match-level interpretation | Future parser tuning as more DEM samples arrive | 9 | High signal: universal CS stat | Done for current MVP |
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
| Mistake detection | 8 | 25% | Basic rule-based weakness detection | Structured mistake objects, evidence, confidence, per-match mistakes; see `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` | 9 | High: users explicitly seek mistake correction | Planned |
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
| Official DEM import | 88% | Real CS2 demo can become match stats; parser confidence, event counts, metric confidence, warnings, swing_score, deep parser artifact and normalized evidence exist | Player picker before save, parsed_payload_verified status, side switching validation | Scope/Leetify demo analysis |
| Bitvise/SFTP demo inbox | 90% | User can upload large demos outside browser | Archive/delete UI | Internal usability |
| Match list page | 100% | See imported games in one place with sorting, pagination and detail links | Future polish: saved views/export | Match history |
| Match filters | 100% | Filter by map/result/source/date/goal status | Future polish: imported date filter | Match history |
| General stats dashboard | 100% | Quick overview with core metrics, trends, map stats, data quality, ADR profile, source breakdown | Future polish: custom widgets | Dashboard overview |
| Trend chart | 45% | Visual progress over recent games | More metric toggles and time ranges | Progress tracking |
| Map stats | 50% | Shows best/worst maps | Map detail page, side splits | Map performance |
| Last 15 vs previous 15 | 80% | Shows recent form changes | Custom periods and better explanations | Progress tracking |
| Rule-based weakness detection | 25% | Gives first coach focus | Evidence examples, confidence, richer rules | Mistake detection |
| Coach report | 55% | Generates actionable written analysis | AI version, better formatting, weekly history | Coach report |
| Separate coach page | 60% | Coach info is separate from stats | Goal controls, recommendation history | Coach experience |
| Active recommendation tracking | 55% | Tracks whether advice is followed | Custom recommendations, lifecycle controls | Differentiator |
| Per-match green/yellow/red status | 65% | User sees whether match helped goal | Evidence modal, status filters | Recommendation tracking |
| DEM-based score/result inference | 45% | Imported demo has map/result/score | Validate side switching across more demos | Match details |
| DEM-based ADR/KD/KAST/entry | 70% | Real demo contributes to coach analysis; deep player_rounds, duels, damage and weapon_stats are persisted | KAST/trade tuning, side-specific splits | Core analytics |
| Report includes active recommendation | 50% | Coach report reflects current training goal | More detailed progress section | Coach report |
| AI coach handoff | 80% | Structured JSON payload and Codex CLI prompt are generated from `/coach`; AI result stores payload snapshot/hash/provider metadata/history; local_llm scaffold exists | Real local model setup, structured sections, feedback loop | AI coach report |
| Aim profile | 75% | Honest aim profile with ADR/KD/HS/opening success/multi-kill/weapon breakdown, estimated accuracy, swing_score and explicit data gaps | Spray/TTK/crosshair after reliable shot/view/position data | Aim stats |
| Steam service bot demo downloader | 75% | Dedicated service bot gets CS2 GC demo URLs by share code, downloads `.dem.bz2`, decompresses and imports `.dem` | Stronger bot hardening, retries/backoff, production scheduler | Automatic match import |
| ImportJob background worker flow | 70% | `steam_import_all` queues/reuses active jobs, web request returns immediately, background task runs sync/download/import, overview shows progress | Durable worker process, retry policy, job detail page | Fast post-match refresh |
| Demo storage lifecycle control | 60% | `/settings/storage`, `GET /api/storage/demos`, manifest, candidates for future raw `.dem` delete; deep parser contract added; delete policy remains off | Add verification status, enable retention policy | Demo storage lifecycle |
| README / worklog docs | 90% | Project is understandable and reproducible; Steam worker and storage lifecycle are documented | Keep updated as UX changes | Developer/product docs |
| Competitor feature matrix | 80% | Gives product direction | Revisit after user testing | Product planning |

## Immediate Build Recommendation

The next best work is not adding many new shiny pages. It is making parsed demo data trustworthy enough to delete raw `.dem` files after import:

1. Approve the final metric/raw-slice schema needed before raw demo deletion.
2. Persist verified parsed payload status per imported demo.
3. Improve round-level evidence: side stats, KAST/trade, early deaths, utility, flash and aim timing.
4. Add production-grade Steam job retries/scheduler.
5. Only then enable raw `.dem` delete policy for successfully verified imports.
