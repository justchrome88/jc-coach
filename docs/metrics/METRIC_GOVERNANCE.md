# Metric Governance

The registry is authoritative for metric identity and assurance state. Domain contracts are authoritative for shared formula boundaries. Executable code is inspected against both; existing persisted values are evidence, not expected truth.

Ground-truth states are `verified`, `partially_verified`, `disputed`, `unknown`, and `not_applicable`. `verified` requires independent evidence across the source boundary; an implementation-reflecting unit test cannot grant it. Product states are `active`, `experimental`, `deprecated`, and `blocked`.

Every observation must retain `match_id`, owner `user_id`, owner Steam identity, player key/Steam identity, parser artifact/version, event-set ID, metric semantic version, and source. A consumer must constrain all applicable identities. Missing semantic-version persistence currently makes the snapshot path unsafe for changed formulas.

Disputed/unknown metrics may be displayed only with an explicit caveat and may not create hard coach decisions. A disputed input already used downstream is retained as historical evidence, marked stale/superseded when supported, recomputed only under authorization, and quarantined from claims until validation passes.

Metric owners must distinguish raw facts, normalized facts, aggregates, display rounding, and external comparator semantics. Playlist labels remain provenance-only unless persisted evidence proves the mode.
