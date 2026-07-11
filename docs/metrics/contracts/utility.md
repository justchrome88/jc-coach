# Utility Contract

Version `2.0.0` stores positive supported HE/molotov/inferno/incendiary evidence as `raw_utility_event_amount` and separates `enemy_utility_damage`, `team_utility_damage`, and `self_utility_damage` only when victim relation is explicit. The legacy `utility_damage`, `he_damage`, and `molotov_damage` keys remain quarantined because their historical enemy/team semantics are ambiguous. Match 124's `149` is raw attribution that includes `5` team damage; matching that total is not validation of enemy-only utility damage.

Weapon names pass through one canonical alias map; for example `ak47` and `weapon_ak47` both resolve to `ak47`. Raw source names may remain in provenance.

Flash assists require accepted `assistedflash`/blind-to-kill correlation and remain separate from ordinary assists. `enemies_flashed` requires enemy identity; a blind count without team relation is not truthfully enemy-only. Detonations prove use, not tactical value, lineup quality, or a grenade rating.
