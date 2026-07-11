> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/metrics/contracts/core_combat.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Core Combat Contract

Coach Metric Pack v1 semantic version `3.0.0` supersedes the v2 trusted subset
for current coach consumers. It uses explicit event teams, complete roster/spawn
participation, remaining-health damage capping, five-second trade lineage and
the shared completed-round boundary. See `../coach/COACH_METRIC_PACK_V1.md`.

Version `2.0.0` uses the shared accepted-match-phase boundary. Kills count accepted enemy deaths attributed to the player and exclude self/world/team kills plus warmup/post-match events. Deaths count accepted player victim events through the final accepted round-end tick. K/D is the two accepted counts divided without substituting one for zero deaths; zero deaths is stored as null/unbounded.

Assists are three explicit keys: `ordinary_assists`, `flash_assists`, and `combined_assists`. The legacy `assists` label means combined assists only for version `2.0.0`. `headshot_kill_rate` is accepted headshot kills divided by accepted kills, displayed as a percentage; it is not head hits divided by hits or weapon head accuracy. The ambiguous `headshot_rate` key is rejected for new snapshots.

Damage uses distinct keys for raw attempted enemy, effective accepted enemy, team, self/world, and utility damage. The ambiguous `damage` key is rejected. Match 124 v3 independently proves 1,643 effective enemy damage and 82.15 ADR from the retained health ledger. Older ambiguous damage/ADR observations remain quarantined.

Opening events are the first valid enemy duel of a played round. Trade facts require team identity and an accepted time window. Missing trade evidence is `unknown`, not false.
