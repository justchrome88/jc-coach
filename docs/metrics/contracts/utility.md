# Utility Contract

Utility damage is positive supported damage attributed to HE, molotov, inferno, or incendiary events, deduplicated across raw hurt and grenade representations. Enemy, team, and self damage must remain distinguishable. Match 124's current `149` is reproducible as raw HE attribution, including `5` team damage; enemy-only semantics are not yet accepted.

Flash assists require accepted `assistedflash`/blind-to-kill correlation and remain separate from ordinary assists. `enemies_flashed` requires enemy identity; a blind count without team relation is not truthfully enemy-only. Detonations prove use, not tactical value, lineup quality, or a grenade rating.
