# Core Combat Contract

Kills count accepted enemy deaths attributed to the player. Exclude self/world/team kills and all non-played phases. Deaths count accepted player victim events in played rounds. Assists retain ordinary and flash-assisted subsets separately. HS% is headshot kills divided by accepted kills; it is not head hits divided by hits or weapon headshot accuracy.

Damage requires explicit victim relation and effective-health semantics. Raw `dmg_health` attempted damage, enemy effective damage, team damage, self/world damage, and utility damage are distinct fields. ADR uses accepted damage divided by accepted player rounds; numerator, denominator, storage precision, and display rounding must be independently evidenced.

Opening events are the first valid enemy duel of a played round. Trade facts require team identity and an accepted time window. Missing trade evidence is `unknown`, not false.
