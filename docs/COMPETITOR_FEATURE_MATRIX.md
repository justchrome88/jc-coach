# HISTORICAL / ADVISORY

This document is retained as competitor research. Current product scope and priorities are governed by `docs/PROJECT_CONTROL.md`, `docs/CURRENT_MILESTONE.md` and `docs/ROADMAP.md`.

# Competitor Feature Matrix

This file tracks features observed in CS2 analytics/training products and estimates implementation difficulty for CS2 Personal Coach.

## Sources

- Scope.gg homepage: https://scope.gg/
- Scope.gg CS2 support announcement: https://blog.scope.gg/scopegg-cs2-en/
- Scope.gg guides: https://scope.gg/guides/
- Leetify homepage: https://leetify.com/
- Leetify stats glossary: https://leetify.com/blog/leetify-stats-glossary/
- Leetify blog / product updates: https://leetify.com/blog/
- Refrag wiki: https://wiki.refrag.gg/
- Refrag homepage: https://refrag.gg/
- Refrag aim page: https://refrag.gg/aim/

## Difficulty Scale

- Easy: can be done with current match table or simple UI/backend work.
- Medium: needs more DEM parsing or moderate product work.
- Hard: needs robust event/round/tick processing, background jobs, or larger architecture.
- Very hard: needs replay systems, video processing, game servers, or large datasets.
- Not realistic now: blocked by missing external data, platform constraints, or cost.

## Matrix

| Feature | Seen In | What It Means | Our Status | Difficulty | Suggested Priority |
|---|---|---|---|---|---|
| Match history | Scope.gg, Leetify | List of analyzed matches with score, map, result, stats | Basic version exists | Easy | Now |
| Dashboard overview | Scope.gg, Leetify | Winrate, K/D, ADR, KAST, rating, form | Basic version exists | Easy | Now |
| CSV/JSON import | Internal MVP need | Manual data ingestion | Exists | Easy | Done |
| Official `.dem` upload | Scope.gg-like analytics | Parse official CS2 demo files | Basic import works | Hard | Now |
| Server-side demo inbox | Internal usability need | Upload via SFTP/Bitvise and import from web UI | Exists | Easy | Done |
| Steam / FACEIT login | Scope.gg, Leetify | Connect external accounts | Not started | Medium | Later |
| Automatic match import | Scope.gg, Leetify | Pull match history automatically | Not started | Hard | Later |
| Map performance | Scope.gg | Stats by map, best/worst maps | Basic version exists | Easy | Now |
| Map-specific coach focus | Scope.gg-like | Recommendations per weak map | Partial | Medium | Next |
| Last period comparison | Scope.gg-like | Compare recent matches vs previous matches | Exists | Easy | Done |
| Progress tracking | Scope.gg, Leetify | Show metric trends over time | Basic chart exists | Easy | Now |
| Active training goal | Internal differentiator | Track whether player follows coach recommendation | Basic version exists | Medium | Now |
| Per-match goal status | Internal differentiator | Green/yellow/red per match | Exists | Medium | Done |
| Coach report | Scope.gg-like | Written analysis and next steps | Basic rule-based exists | Medium | Now |
| AI coach report | Product vision | LLM-written report from aggregated stats | Not started | Medium | Next |
| Recommendation lifecycle | Internal differentiator | Complete, extend, pause, replace goals | Not started | Medium | Next |
| Aim stats | Scope.gg, Leetify, Refrag | HS%, accuracy, first bullet, spray, TTK | Very partial | Hard | Later |
| First duels | Scope.gg | Opening kills/deaths and success | Basic version exists | Medium | Now |
| Early deaths | Scope.gg-like | Death timing by round phase | Fallback only | Hard | Next |
| KAST | Scope.gg/Leetify-style | Kill/assist/survive/trade involvement | Basic best-effort | Hard | Next |
| ADR | Scope.gg/Leetify-style | Average damage per round | Works from DEM damage events | Medium | Done |
| Utility damage | Scope.gg | HE/molotov/incendiary damage | Partial | Medium | Next |
| Flash assists | Scope.gg | Assists caused by flash | Partial | Medium | Next |
| Enemies flashed | Scope.gg | Count and duration of blinded enemies | Not reliable yet | Medium | Next |
| Grenade effectiveness | Scope.gg | Evaluate useful/failed utility | Not started | Hard | Later |
| Grenade lineups library | Scope.gg, Refrag Utility Hub | Learn smokes/flashes/mollies by map | Not started | Medium content-heavy | Later |
| Interactive utility hub | Refrag | Practice and learn utility lineups interactively | Not started | Very hard | Much later |
| Clutch stats | Scope.gg | Clutch attempts, wins, situations | Not started | Hard | Later |
| Economy analytics | Scope.gg | Eco/force/full-buy impact | Not started | Hard | Later |
| Side stats | Scope.gg | T-side/CT-side winrate and performance | Partial through round events | Medium | Next |
| Round-by-round timeline | Scope.gg-like | Every round summary and key events | Not started | Hard | Later |
| Mistake detection | Scope.gg | Detect repeated errors | Basic rule-based exists | Hard to make good | Now/Later iterative |
| Heat maps | Scope.gg | Kill/death/position heat maps | Not started | Very hard | Later |
| Position/callout analysis | Scope.gg/Refrag-like | Weak zones and deaths by position | Not started | Very hard | Later |
| 2D demo viewer | Scope.gg, Refrag | Replay rounds on top-down map | Not started | Very hard | Much later |
| Automatic highlights/clips | Scope.gg, Leetify | Generate clips of best moments | Not started | Very hard | Much later |
| Shareable match reports | Leetify | Public/private report links | Not started | Medium | Later |
| Friend comparison | Leetify | Compare stats/accomplishments with friends | Not started | Medium after users | Later |
| Team contribution / carry detection | Leetify | Who carried and impact by player | Not started | Hard | Later |
| Rank benchmark comparison | Leetify | Compare to players at rank/level | Not available | Not realistic now | Never/only local approximation |
| Public data library | Leetify | Massive aggregated public stats | Not available | Not realistic now | Never for MVP |
| Post-match journal | Leetify | Correlate outside factors with winrate | Not started | Medium | Later |
| Training routines | Refrag | Generated warmup/training tasks | Basic 7-day plan in report | Medium | Next |
| Aim training modes | Refrag | In-game Crossfire/Prefire/Aim trainers | Not started | Very hard | Much later |
| Hosted CS2 practice servers | Refrag | Custom game servers for training | Not started | Very hard/costly | Not now |
| Bootcamp mode | Refrag | Automated complete training flow | Not started | Very hard | Much later |
| Academy videos | Refrag | Curated training video content | Not started | Easy technically, hard content | Later |
| Strategy board | Scope.gg/Refrag-like | Draw plans, setups, tactics | Not started | Medium | Later |
| Team/scrim tools | Refrag-like | Tools for team prep and review | Not started | Hard | Later |

## Suggested Build Order

1. Stabilize DEM import for real files.
2. Improve `/matches` and `/coach` around imported DEM evidence.
3. Add side stats, round score confidence, and better KAST.
4. Add utility/flash metrics from real demo events.
5. Add map-specific coach recommendations.
6. Add AI report using aggregated JSON.
7. Add recommendation lifecycle and progress history.
8. Later: heatmaps, round timeline, clutches, economy.
9. Much later: 2D viewer, clips, Refrag-like training servers.

## Current Product Differentiator

The most valuable near-term feature is not copying every analytics table. It is linking a coach recommendation to future matches and showing whether the player actually changed behavior.
