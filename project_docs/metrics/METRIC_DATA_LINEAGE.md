> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/metrics/METRIC_DATA_LINEAGE.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Metric Data Lineage

## Coach Metric Pack v1 / semantic version 3.0.0

H01A-M04 appends compact `coach-metric-events-v1` files derived from retained
demos. Each v3 performance, utility and aim snapshot retains owner user, owner
Steam ID, measured player, match, original parser artifact, retained demo SHA,
event-set content hash, implementation version and metric semantic version.
Trusted owner/coach selectors accept validated v3 only. Prior parser artifacts,
event sets and v1/v2 snapshots remain immutable historical evidence.

## Version 2 snapshot identity

New critical snapshots constrain `owner_user_id`, match/scope, player identity,
metric domain, semantic version, parser artifact, event-set identity, and
validation state. Input event hashes are deterministic. Version `1.0.0` rows
remain readable as `legacy_unverified`; a version `2.0.0` computation appends a
row and never rewrites the old meaning. Personal selectors require the owner,
player, accepted semantic version when specified, and `validated` state.

Within a domain snapshot, `metadata.metric_validation` records each metric key,
status, and reason codes. Trusted payload serialization removes quarantined or
rejected keys before coach, hypothesis, or mission code sees them.

## H01A concrete chain

`match 123 (owner 17/account 1/import job 101)` → retained demo SHA-1 `fc3aac…6aa` → `match 124` → parser artifact `91`, demoparser2 `0.41.3`, payload `2026-07-02.1` → normalized event set `parser-artifact:91:events:8285d8fafd78be0f` → owner player `steam:76561198056634139` → snapshots `1138` and `1149` → analysis run `59` → hypotheses `110/111`; snapshot `1149` also enters mission `3` progress evaluation `9`.

| Boundary | Input → output identity | Join / owner keys | Dedup/version | Failure and validation |
|---|---|---|---|---|
| retained demo | source match 123 → file SHA-1 | `user_id=17`, `steam_account_id=1`, `import_job_id=101`, demo path/hash | content hash | hash mismatch fails lineage |
| parser | file SHA-1 → artifact 91 / demo match 124 | artifact `match_id`, job ID, source file | unique artifact per match; parser/payload versions persisted | status/gaps/confidence retained; parser rerun not part of this audit |
| normalized facts | artifact payload `deep` → event objects/tables | artifact ID, match ID, round, tick, player Steam IDs | event-set hash; raw/derived representations can duplicate without event-specific keys | schema validation exists; round semantics do not |
| player identity | target `JC` → Steam ID | preferred Steam ID; name fallback in parser | player key | owner scope proves owner 17/account 1; parser fallback remains a general risk |
| participation | round boundaries + player events → player rounds | match/player/round | no accepted versioned participation key | quiet rounds disappear; post-match self-death creates a row |
| aggregation | normalized events → core/utility metrics | match/player/event set | code versions `core-combat-metrics-v1`, `utility-metrics-v1` only in JSON metadata | formula confidence exists, semantic contract enforcement incomplete |
| snapshots | results → `metric_snapshots` | unique `(match_id, player_key, source)` | semantic version is not a DB key; upsert overwrites | unsafe for semantic change/history preservation |
| owner selection | snapshots → analysis scope | match IDs plus player key/Steam ID; owner match join in mission windows | latest ordering, no semantic-version constraint | owner scope is present; version constraint is absent |
| UI | `matches` or snapshot evidence → templates/API | owned match routes; serializer fields | none | UI primarily shows legacy `matches`, while coach uses snapshots |
| coach | snapshots → insight/hypothesis/mission/progress | user, owner Steam ID, player identity, match IDs | snapshot IDs retained, semantic version absent | disputed metrics can remain usable in evaluation-window context |

Unsafe behavior: snapshot upsert and all snapshot selectors lack a first-class semantic-version constraint. Generic `list_metric_snapshots` can order latest values without owner identity; current product call sites constrain match, but the helper is unsafe for personal use without an owned join. Mission window selection constrains owner user/player and match but not semantic version.
