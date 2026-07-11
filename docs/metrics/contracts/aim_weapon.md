# Aim and Weapon Contract

Weapon identity must normalize parser aliases before joining fire, hit, damage, kill, and headshot events. Accuracy is accepted hits divided by accepted shots for the same normalized weapon. It is not damage accuracy or headshot-kill rate.

Version `3.0.0` normalizes aliases before aggregation and retains shot/hurt/death
ticks. It validates `accepted_shots`, `accepted_hits`, `shot_accuracy`,
`head_hits`, `hit_based_headshot_rate`, `first_shots`, `first_shot_hits`,
`first_bullet_accuracy`, `engagements_with_kill`, `first_shot_to_kill_ms`, and
`first_damage_to_kill_ms` under the local engagement contract. Crosshair
placement and spray trajectory remain unavailable because view-angle/bullet
trajectory timelines are not stored.
