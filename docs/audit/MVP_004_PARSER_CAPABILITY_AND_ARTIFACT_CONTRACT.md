# MVP-004 Parser Capability and Artifact Contract

Date: 2026-07-09
Role: 02-Executor
Task: `MVP-004_PARSER_CAPABILITY_AND_ARTIFACT_CONTRACT`
Verdict: `PASS_WITH_WARNINGS`

## Summary

Current parser capability is stronger than a simple match-summary importer:
`app/services/demo_parser.py` uses `demoparser2`, has parser payload version
`2026-07-02.1`, emits a compact parsed payload, stores a
`demo_parse_artifacts` row, and also writes normalized parser tables for
rounds, player-rounds, weapon stats, damage events, duels and grenade events.

The blocker before normalized events, derived context, metrics and AI coach
work is not absence of parser data. It is the absence of a formally accepted
raw parser artifact contract and quality report contract that separate raw
parser evidence from downstream interpretations. Current data is usable for
Tier 1 MVP facts with caveats, but trade/traded-death, side, economy,
positioning, clutch and context-rich fight selection remain gaps.

Recommended next task: `MVP-005_AI_COACH_DATA_CONTRACT_VERTICAL_SLICE`.

## Scope And Safety

Report-only audit. No parser code was changed. No parser jobs, live import,
evaluator/manual evaluator jobs, production DB/schema/data mutation, raw demo
movement/deletion/compression, service/deploy/runtime changes, package changes,
git add, commit or push were performed.

Allowed output file:

- `docs/audit/MVP_004_PARSER_CAPABILITY_AND_ARTIFACT_CONTRACT.md`

Task mapping note: `MVP-004` is a runner/bootstrap ID. It maps to future Phase
4 parser WPs `WP-040..WP-047`, Phase 5 normalized events `WP-050..WP-056` and
Phase 6 derived-context prerequisites. This report does not create a
conflicting canonical numbering system.

## Evidence Read

Hot/context:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`
- `/opt/jc-coach-pm/task_cards/mvp_queue_compact_v1/2026-07-09_MVP-004_PARSER_CAPABILITY_AND_ARTIFACT_CONTRACT_task-card.md`
- `/opt/jc-coach-pm/docs/task_card_profiles/MVP_TASK_CARD_SAFETY_PROFILES.md`

Parser/import/demo/storage evidence:

- `docs/STEAM_IMPORT.md`
- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/DEMO_DEEP_PARSER_TZ_RU.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/METRICS.md`
- `app/services/demo_parser.py`
- `app/services/importer.py`
- `app/services/demo_storage.py`
- `app/services/demo_retention.py`
- `app/services/steam_demo_downloader.py`
- `app/api/routes.py`
- `app/web/routes.py`
- `app/db/models.py`
- `tests/test_demo_parser.py`
- `tests/test_parser_facts_confidence.py`
- `tests/test_demo_storage.py`
- `tests/fixtures/parser/sanitized_parser_payload_c2.json`

Process warning: one `rg` evidence-discovery command searched too broadly
under `docs/` before the candidate set was narrowed. No historical audit files
were opened as source evidence, and no forbidden mutation/action occurred.

## Current Parser Inventory

| Area | Current finding | Evidence |
|---|---|---|
| Adapter/library | `demoparser2` is the parser library. Declared dependency is `demoparser2>=0.41.3`; runtime version is stored via `importlib.metadata.version("demoparser2")`. | `pyproject.toml`; `app/services/demo_parser.py:205-209`, `app/services/demo_parser.py:1612-1616` |
| Parser module | Main adapter is `app/services/demo_parser.py`. | `app/services/demo_parser.py:1-46` |
| Payload version | Current parser payload version is `2026-07-02.1`. | `app/services/demo_parser.py:35`, `app/services/demo_parser.py:321-324` |
| Primary parser function | `parse_demo(path, player_identifier=None)` opens `DemoParser`, reads header, player info, deaths, damage, round, team, weapon, blind, item, grenade and bomb events, plus grenade trajectories. | `app/services/demo_parser.py:205-226` |
| Import wrapper | `import_demo_file(...)` stores raw demo, calls `parse_demo`, applies Steam metadata when provided, persists match fields/raw JSON and saves parser artifacts. | `app/services/demo_parser.py:85-109` |
| Entrypoints | Manual API `/api/import/demo`, inbox API `/api/import/demo/inbox`, web `/upload`, web `/upload/server-demo`, and Steam demo downloader all call parser-backed import paths. | `app/api/routes.py:105-143`, `app/web/routes.py:549-603`, `app/services/steam_demo_downloader.py:312-337` |
| Artifact table | `demo_parse_artifacts` stores parser name/version, payload version, status, source demo path, demo SHA1, event counts, confidence, gaps and payload JSON. | `app/db/models.py:56-72`, `app/services/demo_parser.py:1428-1474` |
| Normalized parser tables | Existing tables include `demo_rounds`, `demo_player_rounds`, `demo_weapon_stats`, `demo_damage_events`, `demo_duels`, `demo_grenade_events`. | `app/db/models.py:75-190`, `app/services/demo_parser.py:1476-1589` |
| Reparse behavior | Current save function deletes prior parser rows for the match across artifact/round/player/weapon/damage/duel/grenade tables, then reinserts current output. | `app/services/demo_parser.py:1428-1439` |
| Storage/retention | Current policy retains raw demos for parser development; delete-after-success is disabled by default. | `docs/STEAM_IMPORT.md:31-35`, `docs/STEAM_IMPORT.md:81`, `app/services/demo_retention.py` |
| Status/confidence | Parser emits `event_counts`, `metric_confidence`, `parser_confidence`, and warnings. | `app/services/demo_parser.py:264-279`, `app/services/demo_parser.py:317-340`, `app/services/demo_parser.py:350-405` |
| Test coverage | Unit tests cover parser output, persistence, duplicate import, retention metadata, date metadata filtering, deep artifacts and disabled delete-after-success. | `tests/test_demo_parser.py:26-221` |

## Current Output Shape

Top-level parsed payload currently includes:

- `status`, `parser`, `parser_version`, `payload_version`;
- `file`, `demo_sha1`, `played_at`, `played_at_source`;
- selected `player`, `available_players`;
- `match` aggregate with result/score/combat/utility/warning metrics;
- `aim_summary`, `weapon_breakdown`, `swing_summary`;
- `deep` payload;
- `aim_data_gaps`, `header`, `event_counts`, `metric_confidence`,
  `parser_confidence`, `warnings`, `message`.

The `deep` payload currently includes:

- `players`;
- `target_player_key`;
- `rounds`;
- `player_rounds`;
- `duels`;
- `damage_events`;
- `blind_events`;
- `grenade_events`;
- `grenade_trajectories`;
- `weapon_stats`;
- `economy_summary`;
- `target_player_summary`;
- `data_gaps`.

This is adequate as a starting artifact, but it is not yet an accepted raw
artifact contract because required field presence, null semantics, stable event
IDs, source event provenance, timestamp normalization, per-field quality and
reparse lineage are not formally defined.

## Tier 1 MVP Data Availability

| Tier 1 field | Current availability | Confidence / caveat | Current source |
|---|---|---|---|
| Match identity | Available as `source="demo"` plus `external_match_id` derived from demo SHA/player/stats. Steam path also carries share-code context outside parser. | Usable for dedupe, but artifact should explicitly carry source candidate identity and import-job link when available. | `Match.source`, `Match.external_match_id`, parsed `demo_sha1` |
| Match date/time | Available, but exact only when Steam GC metadata supplies `steam_gc_match_time`; demo header/file mtime is fallback and must not be exact Steam match date. | Must preserve date source/status. | `docs/STEAM_IMPORT.md:38`, `docs/STEAM_IMPORT.md:79`, `docs/METRICS.md:67-69` |
| Map | Available from demo header when present. | Header availability varies. | `parse_header`, `match.map_name` |
| Playlist/mode | Not exact. Current parser sets `mode="demo"` provenance, not Premier/Competitive/etc. | Must remain provenance-only until future reliable metadata. | Hot docs and Metric Truth |
| Round identity | Available as `round_number` in `deep.rounds`/`demo_rounds`. | Requires stable numbering semantics before normalized events. | `DemoRound.round_number` |
| Round start/end | Available as `start_tick`, `freeze_end_tick`, `end_tick` when events exist. | Optional anchors; early deaths require anchors and no fallback. | `round_start`, `round_freeze_end`, `round_end` |
| Round winner/result | Round winner side/end reason available; match result/score best-effort. | Score/result warning remains until side switching validated. | `DemoRound.winner_side`, `end_reason`, parser warnings |
| Player identity | Available from player info/events as name and SteamID where present. | Target-player selection can be configured but needs artifact-level selector evidence. | `players`, `target_player_key`, `DemoPlayerRound.player_*` |
| Team identity / side | Team number/side partly inferred. | Low confidence; side metrics suppressed for hard diagnosis/recommendation. | Metric Truth, parser warnings |
| Kills/deaths/assists | Available from `player_death`. | High/medium when target player is correctly selected. | `Match`, `DemoPlayerRound`, `DemoDuel` |
| Damage/ADR | Available from `player_hurt`; ADR derived from damage and round count. | Medium/high depending on event and round coverage. | `DemoDamageEvent`, `Match.adr` |
| Bomb plant/defuse/explosion | Available in round payload and `DemoRound` fields for plant tick/site/outcome. | Needs normalized event IDs and source raw row links before derived context. | `bomb_*` events, `DemoRound` |
| Weapon | Available in duels, damage and weapon stats. | Accuracy is low/display-only unless weapon_fire/hit correlation is accepted. | `DemoDuel.weapon`, `DemoWeaponStat` |
| Timestamps/ticks | Ticks available on many events. | Need one canonical timestamp contract: tick, seconds if derivable, round-relative time, and null semantics. | Current event rows |

## Gaps For Impact Leak

Impact Leak can use current facts as caveated evidence, but not yet as a hard
coach vertical slice without a contract:

- `swing_score` exists but is approximate and heuristic; Metric Truth says it
  is warning-only, not a sole hard basis.
- Damage/ADR, kills/deaths and utility damage are usable, but missing
  opportunity context can overstate or understate impact.
- Bomb events exist, but post-plant/retake role, survival, site control and
  round-state context are not modeled.
- Economy is only an item pickup summary, not an accepted economy model.
- Clutch fields on `Match` are currently `None`; clutch model remains
  unavailable.
- Positioning, rotations, spacing and view-angle context are unavailable.
- Fight value is not tied to a normalized event graph with stable round state
  before/after each action.

Required before hard Impact Leak claims:

- per-round event graph with stable IDs and ordering;
- round-state snapshots around kills, damage, utility and bomb events;
- explicit source coverage for kills, damage, utility, bomb and survival;
- accepted impact formula/version with caveats;
- quality gates blocking impact claims when required events are missing.

## Gaps For Bad Fight Selection

Bad Fight Selection needs more than current opening-duel and death-order facts:

- Entry kills/deaths are available at medium confidence, but depend on event
  order and target-player selection.
- Early deaths require round timing anchors and are approximate/warning-only.
- Current `trade_kill` is low confidence because team-side and trade-window
  inference need hardening.
- `traded_deaths` and untraded deaths are unavailable as reliable match
  metrics.
- Side switching/team identity is low confidence, which affects whether a fight
  was tradable, isolated, advantaged or disadvantaged.
- Position/view-angle/timing context is unavailable, so the parser cannot prove
  wide-swing, exposed-angle, spacing or rotation mistakes.

Required before hard Bad Fight Selection claims:

- reliable target/teammate/enemy team mapping by round and side;
- traded/untraded death derivation with trade window, alive-state and distance
  caveats;
- normalized fight event with attacker/victim/assist/blind/smoke fields and
  round-relative timestamp;
- per-fight quality flags that distinguish opening duel, exit/save context,
  disadvantaged fight, isolated death and unsupported inference;
- suppression behavior when side, trade, timing or position evidence is absent.

## Proposed Raw Parser Artifact Contract

Future raw parser artifact v1 should be the immutable parser evidence layer
that downstream normalized-events WPs consume. It should be JSON first, even if
stored in DB text columns initially.

Required top-level shape:

```json
{
  "schema_version": 1,
  "artifact_type": "raw_parser_artifact",
  "artifact_id": "sha256:<parser-input-and-version>",
  "parser": {
    "name": "demoparser2",
    "library_version": "0.x",
    "adapter_version": "wp-040-raw-artifact-v1",
    "payload_version": "2026-07-02.1"
  },
  "source": {
    "demo_sha1": "...",
    "demo_sha256": "...",
    "source_demo_file": "redacted-or-local-path",
    "source_kind": "manual_upload|steam_gc|inbox",
    "steam_share_code_hash": null,
    "import_job_id": null
  },
  "match": {
    "map_name": "de_mirage",
    "played_at": null,
    "played_at_source": "steam_gc_match_time|demo_header|file_modified_fallback|unavailable",
    "match_date_status": "exact_match_date_available|exact_match_date_unavailable|approximate_match_date",
    "mode_provenance": "demo|valve_matchmaking|unknown",
    "playlist_mode_exact": null
  },
  "players": [],
  "rounds": [],
  "events": [],
  "derived_parser_summaries": {},
  "quality": {},
  "reparse": {}
}
```

Required raw event conventions:

- Every emitted event has `event_id`, `source_event_type`, `round_number`,
  `tick`, `round_time_seconds` when derivable, `actor`, `target`, `assist`,
  `weapon`, `raw_fields`, and `field_quality`.
- Event IDs are stable within one artifact and deterministic from event type,
  round, tick, participant keys and raw-row index.
- `raw_fields` preserves compact source row evidence without secrets.
- Nullable fields must mean unavailable, not zero.
- Raw event types must include at least round start/freeze/end, player death,
  player hurt, weapon fire, blind, grenade detonation/startburn, bomb
  beginplant/plant/begindefuse/defuse/explode and item pickup where present.
- Parser summaries may exist, but downstream normalized-event WPs must consume
  raw events and quality metadata rather than treating summaries as source
  truth.

## Proposed Parser Quality Report Contract

Each artifact should carry a machine-readable quality report:

```json
{
  "schema_version": 1,
  "artifact_id": "...",
  "overall_status": "parsed|parsed_with_warnings|failed|partial|unsupported",
  "parser_confidence": "high|medium|low",
  "event_counts": {},
  "field_coverage": {},
  "metric_confidence": {},
  "warnings": [],
  "critical_gaps": [],
  "claim_support": {
    "tier1_match_summary": "supported|warning|blocked",
    "impact_leak": "supported|warning|blocked",
    "bad_fight_selection": "supported|warning|blocked",
    "normalized_events": "supported|warning|blocked"
  },
  "safety": {
    "raw_demo_retention_status": "retained_for_parser_dev",
    "delete_after_success_allowed": false,
    "secrets_present": false
  }
}
```

Minimum quality gates before normalized-events ingestion:

- artifact has parser name/version/payload version/source demo digest;
- player identity and target-player selection are explicit;
- event counts record required Tier 1 event families;
- match date source/status is explicit;
- every required downstream fact has `supported`, `warning` or `blocked`;
- side/trade/economy/positioning/clutch gaps are explicit and cannot be
  silently promoted;
- parser failures preserve retained raw demo metadata without deleting source
  files.

## Proposed Reparse Safety Requirements

Current delete-and-reinsert behavior is simple and likely acceptable for a
single match in a controlled personal app, but future parser WPs should make
reparse safety explicit before larger normalized-event work.

Requirements:

- Reparse must be idempotent by `match_id`, demo digest, parser adapter version
  and payload/schema version.
- New parser artifacts must either replace prior derived rows transactionally
  or preserve old artifact lineage with `supersedes_artifact_id`.
- Reparse must not duplicate matches, parser artifacts, normalized events,
  recommendation evaluations or raw demo copies.
- Reparse must not advance Steam cursor or mutate import job truth unless the
  reparse task explicitly scopes import-job mutation.
- Reparse must not delete/move/compress raw demos unless a future storage WP
  explicitly authorizes it.
- Reparse should produce pre/post counts for affected parser tables when DB
  mutation is authorized by a future task.
- Partial failure must leave the previous accepted artifact usable or mark the
  replacement as failed without silently corrupting downstream consumers.

## Recommended WP-040..WP-047 Sequence

| WP | Title | Purpose | Mutation profile |
|---|---|---|---|
| `WP-040` | Parser Inventory And Contract Acceptance | Accept this inventory, raw artifact target shape, quality report target and reparse requirements. | Report-only |
| `WP-041` | Raw Parser Artifact v1 Schema And Fixture Contract | Define exact JSON schema, event taxonomy, null semantics, stable event IDs and sanitized fixture requirements. | Report/docs/tests only unless explicitly scoped |
| `WP-042` | Parser Quality Report v1 | Implement or specify `overall_status`, event coverage, field coverage, claim support and safety flags. | Parser code only if authorized |
| `WP-043` | Reparse Idempotency And Lineage Contract | Add accepted reparse behavior, lineage/supersession model and duplicate prevention checks. | DB/schema/data only if separately authorized |
| `WP-044` | Tier 1 Raw Event Coverage Gate | Gate match/round/player/combat/damage/bomb/weapon/tick facts for normalized-events ingestion. | Parser/tests only if authorized |
| `WP-045` | Side Team And Trade Hardening Plan | Decide what is needed to upgrade side, trade kills and traded deaths, or keep them blocked. | Report-first; implementation later |
| `WP-046` | Parser Fixture And Regression Pack | Build sanitized artifact fixtures and regression checks for current Tier 1 facts and blocked facts. | Tests/fixtures only if authorized |
| `WP-047` | Parser Acceptance Gate For Normalized Events | Review WP-041..WP-046 evidence and authorize Phase 5 `WP-050..WP-056` normalized events. | Report-only |

## Checks Run

- `git status --short` before work: clean.
- `git branch --show-current`: `cona`.
- Read-only parser/import/storage/code/test inspection only.
- No full tests run, per task card.
- No parser/import/evaluator/manual evaluator commands run.
- `git diff --check`: pass.
- `git status --short` after work: only expected untracked report file,
  `docs/audit/MVP_004_PARSER_CAPABILITY_AND_ARTIFACT_CONTRACT.md`.

## Token / Context Metrics

- PM_CREATE tokens: `UNKNOWN`.
- EXECUTOR tokens: `UNKNOWN`.
- PM_REVIEW tokens: `UNKNOWN`.
- Total cycle tokens: `UNKNOWN`.
- Task verdict: `PASS_WITH_WARNINGS`.
- Quality verdict: pending PM review.
- Broad reads avoided: most historical audit/archive context avoided; one
  broad `rg` discovery command is noted as a process warning.
- Context manifest used: yes.

## Risks / Blockers

- `PASS_WITH_WARNINGS` because the artifact contract is report-only and not
  implemented yet, exact run-log token metrics are unavailable, and one broad
  discovery search exceeded the ideal narrow read set before evidence was
  narrowed.
- No product blocker requires user action for this report.
- Future implementation WPs must separately authorize any parser execution,
  DB/schema/data mutation, fixture generation, package changes or raw demo
  lifecycle work.

## Executor Verdict

`PASS_WITH_WARNINGS`
