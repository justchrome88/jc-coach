# Coach Domain Metric Requirements

H01A-M04 freezes two current production metric domains: `performance` and
`utility`. Three hypothesis families consume them: `survival_opening` and
`bad_fight_trade` from performance, and `utility_value` from utility. The
machine-readable freeze is
`coach-domain-metric-requirements.json`.

The performance domain answers only bounded survival, opening-duel and trade
discipline questions. Its leaf inputs are `rounds_played`, survival/opening
facts, and explicit five-second trade-lineage facts. The utility domain answers
whether effective enemy utility damage changed relative to the player's own
preceding segment. Its primary leaf is `effective_enemy_utility_damage`, with
HE/fire components and `utility_damage_per_round` as transparent context.

Mission 3 must use `effective_enemy_utility_damage` version `3.0.0`. The legacy
`utility_damage` observation is historical raw attribution with ambiguous
enemy/team meaning; it is not an alias and cannot enter current coach logic.

All current consumers select owner/player-bound, validated v3 snapshots. Missing
leaf data produces no hard claim. Single-match thresholds remain descriptive;
rolling mission eligibility additionally requires the minimum sample and
confidence recorded in the manifest.

Other code paths—legacy recommendation analytics, map/economy/swing context,
and opaque composite ratings—were inventoried but are not current production
hypothesis/mission domains for this task.
