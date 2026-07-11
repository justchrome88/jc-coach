# Coach Domain Metric Requirements

H01B-R01 corrects the M04 naming drift. The coach domains are
`impact_leak` and `bad_fight_selection`. `performance`, `utility`, and `aim`
remain the three Coach Metric Pack v1 metric groups/snapshot sources; none is a
product domain.

The machine-readable requirements are in
`coach-domain-metric-requirements.json`, while the complete product boundary is
in `docs/coach/coach-domain-model.json`.

`impact_leak` requires both persisted outcome context and validated impact/death
evidence. `bad_fight_selection` consumes bounded opening, survival, and explicit
trade-lineage facts. Utility and aim may support context, but cannot create a
domain or mission independently.

`utility_value` remains a useful descriptive/context family. Its validated v3
metric work is preserved, including `effective_enemy_utility_damage`, but the
family is not mission-eligible. Historical missions, hypotheses, criteria, and
progress remain evidence and are not silently renamed.

All trusted consumers select owner/player-bound, validated v3 snapshots.
Missing leaf data, weak confidence, unsupported outcome context, or a
noncanonical family produces no hard claim and no mission.
