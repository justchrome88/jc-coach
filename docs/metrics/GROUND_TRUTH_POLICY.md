# Ground Truth Policy

Passing a formula test proves implementation consistency, not independent
truth. Validation requires source evidence independent of the calculation under
test. External comparator values are evidence only and must not be fitted.

Match 124 independently accepts rounds, kills, deaths, K/D, ordinary/flash/
combined assists, headshot kills, and headshot-kill rate. Effective enemy damage,
ADR, KAST trade state, and three quiet-round participation states remain
disputed. Their values are quarantined, unavailable to trusted owner UI, and
removed from coach/hypothesis/mission inputs until evidence closure.

Evidence priority for demo-derived metrics:

1. retained demo identity/hash plus a reproducible, versioned parser event ledger;
2. independently audited normalized events with player/team/round identity;
3. accepted golden fixtures derived independently of the implementation;
4. persisted aggregates and snapshots;
5. UI/API serialization;
6. external services as semantic comparators only.

An external value may expose a defect but cannot choose the product formula. UI values cannot validate their own persistence source. Unit tests that calculate expectations through the same helper are circular.

A discrepancy verdict is `MATCH`, `MISMATCH`, `SEMANTIC_DIFFERENCE`, `INSUFFICIENT_EVIDENCE`, or `NOT_IMPLEMENTED`. A repair requires a localized layer and accepted semantics. Unresolved guesses are quarantined and excluded from M02 formula changes.

For player metrics, owner identity and measured player identity are separate. Name matching is fallback evidence, never equivalent to a proven Steam ID. Team, self, world, warmup, post-round, post-match, disconnect/reconnect, side-switch, incomplete-round, and overtime treatment must be explicit.
