# WP-017I Match Mode Classification Diagnosis Report

Date: 2026-07-05

## RESULT: DIAGNOSED

Current persisted data cannot reliably distinguish Premier, Competitive,
Wingman, Casual, Deathmatch, FACEIT/custom or other exact playlist modes for
the 22 playable demo matches.

The current data can distinguish parser/import provenance and generic Valve
official match provenance for many rows, but not exact Valve playlist mode.
`mode=demo` is parser/import provenance. `mode=Valve Matchmaking` on
`steam_history` rows is generic provenance and is not accepted as
Premier/Competitive/Wingman proof.

## Product Version Observed

`v0.8`

Target remains `v0.9` Real Data Onboarding / Bulk Demo Usage.

## DB SHA

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA unchanged after diagnosis: yes.

## Data Sources Inspected

Docs:

- `AGENTS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/audit/WP_017R_ROADMAP_WP_REGISTRY_GOVERNANCE_REPAIR_REPORT.md`
- `docs/audit/WP_017G_POST_BATCH_DATA_INTEGRITY_ACCEPTANCE_REPORT.md`
- `docs/audit/WP_017H_POST_BATCH_PERFORMANCE_ACCEPTANCE_REPORT.md`
- `docs/audit/WP_017A_REAL_DATA_ONBOARDING_DIAGNOSIS.md`

Code:

- `app/db/models.py`
- `app/services/demo_parser.py`
- `app/services/steam_demo_downloader.py`
- `app/services/steam_integration.py`
- `app/services/steam_match_metadata.py`
- `app/services/metric_confidence.py`

Read-only DB areas:

- `matches.mode`
- `matches.source`
- `matches.raw_json`
- `steam_history` rows and `raw_json`
- `imported_demo_match_id` links
- `demo_parse_artifacts.payload_json`
- `demo_parse_artifacts.confidence_json`
- parser header/server metadata persisted in artifact payloads

## Mode Signal Inventory

| Signal | Classification | Finding | Reliability |
|---|---|---|---|
| `matches.source=demo` | parser/import provenance | All 22 playable demo matches are stored as source `demo`. | reliable provenance, not playlist |
| `matches.mode=demo` | parser/import provenance | Parser sets mode to `demo` for imported playable rows. | reliable provenance, not playlist |
| `matches.source=steam_history` | Steam share-code placeholder provenance | 54 rows are Steam history placeholders. | reliable provenance, not playlist |
| `steam_history.mode=Valve Matchmaking` | generic Valve matchmaking label | All Steam history rows use this label. | generic only; not Premier/Competitive/Wingman proof |
| `matches.raw_json.steam_metadata` | Steam GC metadata | Contains `match_id`, `match_time`, `share_code`, and `raw_gc_metadata.watchable_match_info`. | proves Steam GC date/demo provenance, not playlist |
| `steam_metadata.raw_gc_metadata.watchable_match_info` | watch/demo metadata | Contains server IP, TV port, spectators and decrypt key. | not playlist |
| parser `header.server_name` | Valve server provenance | Values look like `Valve Counter-Strike 2 ... Server`. | generic Valve server only |
| parser `header.map_name` | map | Persists map name. | map only; must not infer playlist |
| parser `header.game_directory`, `client_name`, `demo_version_name` | parser/header metadata | Confirms SourceTV/CS2 demo format. | not playlist |
| `demo_parse_artifacts.confidence_json` | parser metric confidence | Contains metric confidence, not match playlist. | not playlist |

No persisted key path containing a reliable playlist/mode label was found. The
only mode-like persisted paths were `match.mode`, `header.server_name`, and
`steam_metadata.raw_gc_metadata.watchable_match_info.server_ip`.

## Per-Match Classification Summary

| Match | Map | Played at | Persisted mode/provenance | Possible playlist classification | Confidence | Evidence field | Reason |
|---:|---|---|---|---|---|---|---|
| `#21` | `de_overpass` | `2026-06-05 19:19:11` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#22` | `de_dust2` | `2026-06-05 20:07:29` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#23` | `de_mirage` | `2026-06-05 20:35:43` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#24` | `de_ancient` | `2026-06-05 21:02:13` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#25` | `de_cache` | `2026-06-06 17:31:48` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#26` | `de_dust2` | `2026-06-06 18:06:28` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#27` | `de_dust2` | `2026-06-06 18:49:28` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#28` | `de_ancient` | `2026-06-06 19:18:01` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#29` | `de_nuke` | `2026-06-06 19:56:34` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#30` | `de_overpass` | `2026-06-11 18:32:26` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#31` | `de_dust2` | `2026-06-11 19:12:11` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#32` | `de_ancient` | `2026-06-11 20:00:51` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#33` | `de_ancient` | `2026-06-12 18:59:06` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#34` | `de_inferno` | `2026-06-12 19:18:19` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#35` | `de_nuke` | `2026-06-12 20:09:36` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#36` | `de_dust2` | `2026-06-13 13:05:11` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#37` | `de_overpass` | `2026-06-30 19:36:28` | `demo/demo` | unknown | unknown | parser header only | No Steam playlist metadata persisted. |
| `#38` | `de_dust2` | `2026-07-01 08:59:36.754534` | `demo/demo` | unknown | unknown | parser header only | No Steam playlist metadata persisted. |
| `#70` | `de_overpass` | `2026-07-03 19:34:35` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#72` | `de_dust2` | `2026-07-04 15:31:49` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#76` | `de_mirage` | `2026-07-04 20:04:48` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |
| `#75` | `de_overpass` | `2026-07-04 20:26:32` | `demo/demo` | Valve official match, playlist unknown | unknown | `steam_metadata.raw_gc_metadata` | GC metadata has match id/time/watch info only. |

## Recent Match Findings

### Match `#72` `de_dust2`

- Persisted `matches.mode`: `demo`.
- Linked Steam history row: `#71`, `mode=Valve Matchmaking`.
- `steam_metadata`: has `match_id=3829347978032709907`, `match_time`,
  `share_code`, and `watchable_match_info`.
- Parser header: Valve CS2 server, map `de_dust2`, SourceTV demo.
- Reliable playlist: unknown.

### Match `#75` `de_overpass`

- Persisted `matches.mode`: `demo`.
- Linked Steam history row: `#74`, `mode=Valve Matchmaking`.
- `steam_metadata`: has `match_id=3829385951986057714`, `match_time`,
  `share_code`, and `watchable_match_info`.
- Parser header: Valve CS2 server, map `de_overpass`, SourceTV demo.
- Reliable playlist: unknown.

### Match `#76` `de_mirage`

- Persisted `matches.mode`: `demo`.
- Linked Steam history row: `#73`, `mode=Valve Matchmaking`.
- `steam_metadata`: has `match_id=3829383151667380326`, `match_time`,
  `share_code`, and `watchable_match_info`.
- Parser header: Valve CS2 server, map `de_mirage`, SourceTV demo.
- Reliable playlist: unknown.

Operator memory is not persisted proof and was not used.

## Recoverability Decision

| Question | Decision |
|---|---|
| Recoverable now from persisted data | No. |
| Recoverable for historical rows without external calls | No. |
| Recoverable only for future imports if extra metadata is captured | Potentially yes, if Steam GC/helper output exposes a reliable playlist/mode field and the app persists it. |
| Requires external Steam API/GC call for historical rows | Yes, if exact historical playlist labels are required. Not authorized in WP-017I. |
| Requires schema/UI change | Likely yes for a clean first-class playlist field; raw JSON capture may be possible first, but UI/report labels need product code changes. |
| Should current rows remain unknown | Yes. |

Current data cannot distinguish:

- Premier: no reliable persisted proof.
- Competitive: no reliable persisted proof.
- Wingman: no reliable persisted proof.
- Casual: no reliable persisted proof.
- Deathmatch: no reliable persisted proof.
- FACEIT/custom: no reliable persisted proof in current rows.

## Reliability Decision

Accepted reliable labels:

- `demo`: parser/import provenance only.
- `Valve Matchmaking`: generic Steam/Valve share-code provenance only.
- `steam_gc_match_time`: reliable exact date source.

Rejected for exact playlist classification:

- map name;
- round score;
- operator memory;
- `mode=demo`;
- `mode=Valve Matchmaking`;
- Valve server name;
- Steam GC `watchable_match_info` without a playlist/mode field.

## Recommended WP-017J Path

Recommended path: `Explicit Deferral` for historical playlist classification,
with a future capture repair parked for later.

WP-017J should document that current historical rows remain playlist `unknown`
for `v0.9`, verify user-facing labels do not claim Premier/Competitive/Wingman,
and carry a future repair item to capture reliable playlist metadata on future
imports if Steam GC/helper data exposes it.

Do not run live Steam/Valve imports, parser jobs or external recovery calls just
to classify historical mode in WP-017J unless a future WP explicitly authorizes
that risk.

## Whether Match Mode Blocks v0.9

Not if WP-017J explicitly accepts this limitation.

Match mode should block `v0.9` only if `v0.9` claims playlist-specific filtering,
Premier/Competitive/Wingman analytics, or mode-specific recommendation quality.
For controlled personal Real Data Onboarding, mode can remain unknown if the
limitation is named and carried into WP-017K.

## Required Limitation Text For WP-017K

Use this limitation text in WP-017K if WP-017J accepts deferral:

```text
Match playlist mode is not accepted as exact in v0.9. Current persisted data
distinguishes parser/import provenance (`demo`) and generic Valve share-code
provenance (`Valve Matchmaking`), but it does not reliably distinguish Premier,
Competitive, Wingman, Casual, Deathmatch, FACEIT or custom modes. No
playlist-specific claims, filters or recommendations are accepted in v0.9 unless
future WPs capture reliable mode metadata.
```

## Verification

Initial required commands were run:

```text
git status --short
git log --oneline -30 --decorate
sha256sum data/cs2_coach.db
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
```

Final required commands were run:

```text
git diff --check
python3 scripts/project_gate.py postflight
sha256sum data/cs2_coach.db
```

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | no; read-only SQLite URI used |
| production files touched | no runtime data files touched |
| live import/parser run | no |
| live Steam/Valve import run | no |
| demo download run | no |
| manual evaluator run | no |
| persistent app report generated | no |
| schema changed | no |
| cap changed | no |
| raw demos deleted/moved/compressed | no |
| runtime code changed | no |
| tests changed | no |
| v0.9 promotion made | no |
| commit made | no |

## Next WP

`WP-017J Match Mode Classification Repair / Labels, Or Explicit Deferral`.
