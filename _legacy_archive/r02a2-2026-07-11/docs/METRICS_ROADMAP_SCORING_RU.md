> Status: Supporting / historical metric scoring evidence; not current
> product, roadmap, workflow or source-of-truth.
> Use as supporting history only. This file must not override `AGENTS.md`,
> `docs/CURRENT_STATUS.md`, `docs/project_management/WP_REGISTRY.md` or current
> Task Cards.
> Current metric truth: `docs/METRICS.md`.
> Current roadmap/version truth: `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md` and
> `docs/project_management/VERSION_ROADMAP.md`.
> Current workflow truth: `docs/project_management/AGENT_WORKFLOW.md`.
> Navigation/classification: `docs/project_management/DOCS_INDEX.md` and
> `docs/project_management/DOCS_MAP.md`.

# Матрица метрик CS2

Отдельная от roadmap фич таблица: что считать из DEM/API/imports, насколько это полезно пользователю и насколько сложно внедрить корректно.

| Метрика | Категория | Полезность | Сложность | Готовность | Что уже есть | Что нужно дописать | Приоритет |
|---|---|---:|---:|---:|---|---|---|
| Swing / Round Swing | Impact | 10 | 7 | 45% | matches.swing_score, raw_json.swing_summary, artifact payload; jc_swing_v1 на death/bomb/damage/flash events; UI/API/dashboard/stats/matches; backfill 18 DEM матчей | Economy-adjustment, map/side model, verified side switching, round outcome distribution, richer per-round UI | Доводить сейчас |
| ADR | Damage | 10 | 3 | 100% | matches.adr из DEM player_hurt и CSV/JSON; агрегаты/UI/API | Только tuning по новым DEM samples | Готово |
| K/D, KPR, DPR | Combat | 9 | 2 | 90% | kills/deaths/kd; KPR/DPR можно вывести из rounds | Добавить явные KPR/DPR поля в summary/UI | Быстро добавить |
| KAST | Participation | 9 | 6 | 55% | best-effort KAST из kill/assist/survive | Trade detection, team context, full round participation | Доводить |
| Opening duels | Entry | 9 | 5 | 75% | entry_kills/deaths, opening_duel_success, first deaths by round | First contact timing, side/map context, trade after entry | Доводить |
| Trade kills / traded deaths | Teamplay | 9 | 6 | 25% | trade_kill flag in demo_duels approximation | Strict trade windows, team side validation, UI/API aggregation | Следующим этапом |
| Utility damage | Grenades | 8 | 4 | 70% | utility_damage из player_hurt weapon type | Owner attribution tuning for molotov/incendiary/smoke edge cases | Доводить |
| Enemies flashed / flash assists | Grenades | 8 | 5 | 55% | player_blind, assistedflash, grenade events | Enemy-only/team filter, duration thresholds, useful flash model | Доводить |
| Accuracy / hit rate | Aim | 8 | 5 | 60% | estimated accuracy from weapon_fire/player_hurt in demo_weapon_stats | Bullet-level hit model, weapon filters, wallbang/no-damage handling | Доводить |
| Headshot % | Aim | 7 | 2 | 90% | headshot_percent из death events/imports | Weapon/side splits | Готово для MVP |
| Multi-kills | Impact | 7 | 4 | 65% | multi_kill_rounds in aim summary | 1k/2k/3k/4k/5k distribution and round outcome correlation | Доводить |
| Clutch attempts/wins | Clutch | 8 | 7 | 10% | schema fields exist, no reliable parser yet | Alive state timeline, 1vX detection, save/clutch separation | Позже после round state |
| Economy-adjusted impact | Economy | 8 | 8 | 0% | Нет | Equipment/money parsing, buy classification, eco/full-buy weights | Позже |
| Crosshair placement | Aim | 8 | 9 | 0% | Data gap documented | View angles, enemy positions, visibility model | Позже |
| Time to damage / TTK | Aim | 7 | 8 | 0% | Data gap documented | Shot/damage timeline, encounter detection, visibility timing | Позже |
| Spray control / first bullet accuracy | Aim | 7 | 9 | 0% | Data gap documented | Bullet trajectories/view punch/recoil model | Позже |
| Positioning / spacing | Positioning | 9 | 9 | 0% | Нет | Player positions, teammate distance, trade opportunity model | Сильно позже |
| Heatmap death/kills | Map | 7 | 8 | 10% | Event positions partially available for grenade/bomb, not player positions stored | Map coordinate transforms, player positions, UI renderer | Позже |
| Side T/CT splits | Side | 8 | 5 | 20% | side stats marked low confidence | Reliable side switching and player team mapping per round | Следующим этапом |
| Bomb impact | Objective | 7 | 5 | 35% | bomb events stored, basic swing credit for plant/defuse/explosion | Plant/defuse context, postplant survival, retake model | Доводить |
| RWS / Round Win Shares | Impact | 7 | 7 | 15% | Conceptually related to swing; no separate RWS field | Round win contribution model and distribution among winners | После swing v1 |
| Leetify-style rating buckets | Composite | 7 | 8 | 0% | Нет | Normalize aim/utility/positioning/clutch into comparable scores | Позже |
| HLTV-like Rating | Composite | 8 | 7 | 20% | rating field exists for imports; no custom rating formula | Kills/damage/survival/KAST/multi/swing normalization | Позже после базовых метрик |

## Источники

- FACEIT Round Swing: https://support.faceit.com/hc/en-us/articles/27123235446428-FACEIT-Season-8-Understanding-Round-Swing
- FACEIT Rating FAQ: https://support.faceit.com/hc/en-us/articles/26530513602716-FACEIT-Season-8-FACEIT-Rating-FAQ
- FACEIT CS2 Advanced Stats / RWS: https://support.faceit.com/hc/en-us/articles/19309126922140-FACEIT-CS2-Advanced-Stats
- HLTV Rating 3.0: https://www.hltv.org/news/42485/introducing-rating-30
- HLTV Rating 3.0 adjustments: https://www.hltv.org/news/43047/rating-30-adjustments-go-live
- Leetify stats glossary: https://leetify.com/blog/leetify-stats-glossary/
- Leetify homepage examples: https://leetify.com/
- Scope CS2 support/features: https://blog.scope.gg/scopegg-cs2-en/
- Scope homepage metrics: https://scope.gg/
- Implementation update: 2026-07-02: swing_score/jc_swing_v1 implemented in parser, DB, API, UI; backfilled for 18 valid DEM matches.
