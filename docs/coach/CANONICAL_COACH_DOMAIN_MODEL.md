# Canonical Coach Domain Model

H01B-R01 freezes exactly two MVP coach domains:

1. `impact_leak` — **Impact Leak / Useful vs Useless Deaths**.
2. `bad_fight_selection` — **Bad Fight Selection / Duel Discipline**.

`performance`, `utility`, and `aim` are metric groups and persisted snapshot
sources. They are not product domains. A hypothesis family is an implementation
classification, not a domain, and a mission id is historical identity, not a
domain key.

The machine-readable authority is [coach-domain-model.json](coach-domain-model.json).
It records each domain's purpose, evidence boundary, forbidden claims, families,
metrics, sample/confidence floor, missing-data behavior, and suppression policy.

## Family reconciliation

| Family or legacy alias | Canonical classification | Decision |
|---|---|---|
| `impact_leak` | `impact_leak` | Canonical family. |
| `survival_opening` | `bad_fight_selection` | Its current intervention changes opening/survival fight discipline, not outcome conversion. |
| `bad_fight_trade` / `trade_discipline` | `bad_fight_selection` | Bounded duel/trade context only; no spatial cause claim. |
| `bad_fight_selection` | `bad_fight_selection` | Canonical family. |
| `utility_value` | `context-only` | Useful metric/trend evidence, but its standalone utility-improvement claim does not fit either approved domain. It is not mission-eligible. |
| `performance` / `utility` | `deprecated/unmapped` | Historical mislabeling of metric groups as product domains. |
| `aim` | `context-only` | Metric group only. |

The mapping deliberately does not force `utility_value` into `impact_leak`:
mission 3's intervention was to recover utility damage itself, without an
outcome-conversion or death-usefulness claim. Reclassification would rewrite its
meaning.

## Selection model

No earlier canonical product decision selected global versus per-domain active
missions. H01B-R01 therefore preserves the safest MVP behavior required by the
task: **at most one active mission globally per owner**. A supported second
domain remains a candidate while another mission is active; it is not activated
in parallel. Zero active missions is valid when no canonical hypothesis passes.

Legacy rows remain historical evidence. Trusted serializers expose an approved
canonical domain or `null`, while retaining the original payload as
`legacy_domain_key` evidence where relevant.
