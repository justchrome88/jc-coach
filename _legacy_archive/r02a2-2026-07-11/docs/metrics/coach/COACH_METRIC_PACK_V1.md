# Coach Metric Pack v1

Coach Metric Pack v1 is the explainable, owner-scoped metric set persisted as
semantic version `3.0.0`. Its three append-only snapshot sources are
`coach_metric_performance`, `coach_metric_utility`, and `coach_metric_aim`.
Older v1/v2 snapshots remain historical and are not selected by trusted coach
consumers.

## Shared boundaries

- Phase: completed regulation and overtime rounds only, through the inclusive
  final `round_end` tick. Warmup, incomplete rounds and post-match events are
  excluded.
- Participation: roster or spawn membership plus connect/disconnect and team
  evidence. Quiet rounds remain participated; missing combat is never absence.
- Team: explicit `team_num` at the event or proven round roster. Names are not
  team evidence.
- Damage: raw attempted damage is separated from effective enemy, team,
  self/world and unclassified damage. Effective damage is capped against the
  victim's remaining accepted round health.
- Trade: a five-second, same-round attacker/victim lineage with explicit teams.
  A trade opportunity is a deterministic teammate-death lineage, not a claim
  that the owner was spatially able or tactically expected to trade.
- Engagement: begins at an accepted firearm shot; ends on a gap over 80 ticks
  (1.25 seconds), weapon switch, owner kill/death, utility damage interaction or
  round end. Multiple enemies may occur in one engagement.

## Performance

`KPR = kills / rounds_played`. `survival_rate = survived_rounds /
rounds_played`. `ADR = effective_enemy_damage / rounds_played`. `KAST` is the
percentage of participated rounds with at least one accepted kill, assist,
survival or traded death, counting a round once. The opening duel is the first
accepted enemy kill in a round. Multi-kills retain 2K, 3K, 4K and 5K+ buckets.

Assists remain `ordinary_assists`, `flash_assists`, and `combined_assists`.
`headshot_kill_rate` is headshot kills divided by kills and is not the aim
metric `hit_based_headshot_rate`.

## Utility

`effective_enemy_utility_damage = enemy_he_damage + enemy_fire_damage`, after
team/self exclusion and effective-health capping. `utility_damage_per_round`
uses `rounds_played`. Detonations prove use only. Enemy flash count and duration
require explicit team relation; duration is clipped at accepted round end.

The legacy keys `utility_damage`, `he_damage`, and `molotov_damage` are not
mapped into this pack.

## Aim primitives

`shot_accuracy = accepted_hits / accepted_shots * 100`.
`hit_based_headshot_rate = head_hits / accepted_hits * 100`.
`first_bullet_accuracy = first_shot_hits / first_shots * 100`; a first shot is
successful when an accepted enemy hurt follows it before the second shot and
within eight ticks. `first_shot_to_kill_ms` and `first_damage_to_kill_ms` are
separate mean values over killed engagements. They are local transparent
contracts and do not claim identity with SCOPE.GG or another product.

## Dimensions and aggregation

Snapshots materialize player-match primitives once. Metadata records map,
T/CT side ledgers, weapon-class samples, sample counts, confidence, version and
availability. Rolling, map, side and weapon views aggregate those primitives at
query time; unnecessary cross-products are not persisted. A zero denominator
produces `null` plus `unavailable_metrics`, never a fabricated zero rate.

## Coverage benchmark

Public SCOPE.GG families are used only as a coverage checklist: ADR/KPR/KD/KAST,
shot and head-hit accuracy, first-bullet accuracy, separate local timing
primitives, flash duration, grenade damage, and smokes used. Proprietary or
undocumented ratings are excluded.
