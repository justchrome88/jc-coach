# Core Combat Contract

Version `2.0.0` uses the shared accepted-match-phase boundary. Kills count accepted enemy deaths attributed to the player and exclude self/world/team kills plus warmup/post-match events. Deaths count accepted player victim events through the final accepted round-end tick. K/D is the two accepted counts divided without substituting one for zero deaths; zero deaths is stored as null/unbounded.

Assists are three explicit keys: `ordinary_assists`, `flash_assists`, and `combined_assists`. The legacy `assists` label means combined assists only for version `2.0.0`. `headshot_kill_rate` is accepted headshot kills divided by accepted kills, displayed as a percentage; it is not head hits divided by hits or weapon head accuracy. The ambiguous `headshot_rate` key is rejected for new snapshots.

Damage uses distinct keys for raw attempted enemy, effective accepted enemy, team, self/world, and utility damage. The ambiguous `damage` key is rejected. Match 124 does not independently prove the effective-health numerator, so effective damage and ADR remain quarantined. Raw attempted damage may be retained as evidence but cannot be presented as scoreboard-equivalent ADR.

Opening events are the first valid enemy duel of a played round. Trade facts require team identity and an accepted time window. Missing trade evidence is `unknown`, not false.
