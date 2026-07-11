# Mission Lineage and Selection Model

## Decision

H01B-R02 permits at most one active mission per owner and canonical domain.
Impact Leak and Bad Fight Selection missions may coexist. Zero active missions
is valid.

Mission activation accepts only `impact_leak` or `bad_fight_selection`.
Suppression is owner-and-domain scoped, while the candidate retains its canonical domain
for explanation and later selection. `utility_value`, metric groups, unknown
aliases, and missing domain identity fail closed.

## Production inventory and mission 3

All rows, criteria, evaluations, and payloads are retained:

| Mission | Status after H01B-R01 | Historical family/domain | Intervention | Criteria lineage | Decision |
|---|---|---|---|---|---|
| 1 | cancelled | no explicit key; utility follow-through | Improve legacy `utility_damage` | 1/2 | Historical evidence only. |
| 2 | cancelled | `utility_value` | Increase legacy `utility_damage` | 3/4 | Previously superseded by utility-semantics repair. |
| 3 | cancelled | `utility_value` | Recover effective utility damage toward a personal baseline | 5/6 legacy superseded; 7/8 validated v3 | Superseded by H01B-R01. |

Mission 3 cannot be reclassified without changing its claim. Its original
problem and intervention improve utility damage itself; they do not diagnose
outcome conversion/death usefulness or bad-fight selection. The production row
therefore preserves id `3`, hypothesis `109`, all criteria and all progress,
appends `canonical-domain-reconciliation-v1`, and records the terminal reason
`noncanonical_domain_reconciliation`. No historical domain key was renamed.

The isolated replay activated replacement mission `4` only after a validated
`bad_fight_selection` candidate. Production was intentionally left with zero
active missions because replay-only evidence was not promoted as a new
production hypothesis/mission.

## Lifecycle rules

- Domain identity comes from an explicit canonical mapping, never a mission id.
- `survival_opening`, `bad_fight_trade`, and `trade_discipline` map explicitly
  to `bad_fight_selection`.
- `utility_value` remains context-only and cannot activate or suppress as a
  domain.
- Historical serializers expose `domain_key: null` plus `legacy_domain_key`
  for noncanonical rows.
- Replacement cancels the existing owner mission through the lifecycle helper;
  it never deletes missions, hypotheses, criteria, or evaluations.
