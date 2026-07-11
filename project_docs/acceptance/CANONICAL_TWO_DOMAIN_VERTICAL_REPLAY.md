> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/acceptance/CANONICAL_TWO_DOMAIN_VERTICAL_REPLAY.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Canonical Two-Domain Vertical Replay Acceptance

H01B-R01 result: `PASS_WITH_WARNINGS`. The only warning is the accepted
Starlette TestClient/httpx deprecation warning.

## Accepted architecture

- Coach domains: `impact_leak`, `bad_fight_selection` only.
- Metric groups/snapshot sources: `performance`, `utility`, `aim`.
- `utility_value`: validated context-only family; no candidate, mission, domain,
  or suppression authority.
- Active mission model: at most one per owner and canonical domain; no global
  cross-domain suppression.
- Mission 3: historically preserved and cancelled with
  `noncanonical_domain_reconciliation`.

## Replay evidence

The reusable harness is `scripts/run_canonical_domain_vertical_replay.py` with
`baseline`, `chronological`, `state-matrix`, and `idempotency` modes. Applied
modes refuse the production DB and production artifact root.

The ten retained matches replayed chronologically through real retained-demo
parsing, Coach Metric Pack v1 calculation/persistence, canonical rolling
hypothesis generation, mission selection, and progress evaluation. Each match
produced exactly three validated v3 metric-group snapshots with correct
owner/player/parser/event-set provenance. Independent damage, ADR, KAST,
opening-death, and utility ledgers matched every persisted snapshot.

`bad_fight_selection` became eligible after match 35 and activated one isolated
mission. `impact_leak` became supported at match 79 from repeated high-impact
non-wins (35 and 79) plus death-cost/outcome context, but global suppression
correctly prevented a second simultaneous mission. Negative real subsets were
30/33/117/122/124 for Impact Leak and 33/91/112 for Bad Fight Selection;
early replay prefixes supplied insufficient-data non-claims.

All S1-S10 recovery states passed. S4 and S9 restored complete v3 metric-group
lineage; S10 double submit reused stable identities. The repeat replay changed
zero snapshot, analysis-run, hypothesis, mission, or progress row counts and
left no duplicate v3 identities.

## Full stack

An actual Uvicorn service was run against the isolated replay DB and artifact
root. Health, authenticated dashboard, matches, analytics, coach payload, coach
UI, and technical coordinator routes returned 200. The owner payload exposed
validated v3 scope and one `bad_fight_selection` mission. Unauthenticated coach
API access returned 401. The run also found and fixed the coach-payload Match
serializer boundary; focused and full-suite tests cover it.

No live Steam action, new download, production parser/evaluator job, raw-demo
mutation, dependency change, deployment change, or service restart occurred.
