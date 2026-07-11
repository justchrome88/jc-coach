# Utility Contract

Coach Metric Pack v1 semantic version `3.0.0` defines
`effective_enemy_utility_damage`, `enemy_he_damage`, `enemy_fire_damage`, and
`utility_damage_per_round`. Explicit event teams exclude team/self damage and a
remaining-health ledger caps overkill. The legacy `utility_damage`, `he_damage`,
and `molotov_damage` keys remain quarantined and are not aliases.

Version `2.0.0` remains historical raw attribution. Match 124's legacy `149`
includes `5` team HE damage; v3 therefore records `144` effective enemy utility
damage.

Weapon names pass through one canonical alias map; for example `ak47` and `weapon_ak47` both resolve to `ak47`. Raw source names may remain in provenance.

Flash assists require accepted `assistedflash`/blind-to-kill correlation and remain separate from ordinary assists. `enemies_flashed` requires enemy identity; a blind count without team relation is not truthfully enemy-only. Detonations prove use, not tactical value, lineup quality, or a grenade rating.
