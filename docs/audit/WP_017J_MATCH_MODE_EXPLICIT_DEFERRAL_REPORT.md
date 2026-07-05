# WP-017J Match Mode Explicit Deferral Report

Date: 2026-07-05.

## RESULT

`DEFERRED_ACCEPTED`

WP-017I diagnosis is accepted: current persisted data cannot reliably
distinguish exact Valve playlist mode. WP-017J formally accepts that `v0.9`
will not include exact playlist mode classification.

## Product Version Observed

- Current Product Version: `v0.8`
- Target Version: `v0.9`
- Next WP after this report: `WP-017K Real Data Onboarding Promotion to v0.9`

## DB SHA

Before WP-017J:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Final SHA must match this value in the postflight evidence.

## WP-017I Diagnosis Accepted

Yes.

Accepted facts:

- `matches.mode=demo` is parser/import provenance only.
- `steam_history.mode=Valve Matchmaking` is generic Steam share-code
  provenance only.
- Steam GC match time proves exact date/demo provenance, not exact playlist.
- Map name, score, server name and operator memory are not accepted as exact
  playlist proof.
- Current historical rows should remain playlist `unknown`.

## Exact Limitation Accepted

Match playlist mode is not accepted as exact in v0.9. Current persisted data
distinguishes parser/import provenance (`demo`) and generic Valve share-code
provenance (`Valve Matchmaking`), but it does not reliably distinguish Premier,
Competitive, Wingman, Casual, Deathmatch, FACEIT or custom modes. No
playlist-specific claims, filters or recommendations are accepted in v0.9 unless
future WPs capture reliable mode metadata.

## Labels Allowed In v0.9

- `mode_unknown`
- `provenance_demo`
- `provenance_valve_matchmaking`
- `exact_date_source=steam_gc_match_time`

These labels are provenance/limitation labels, not playlist proof.

## Labels Forbidden In v0.9

The following labels must not be applied to historical rows or used for
playlist-specific claims unless a future WP captures reliable mode metadata:

- Premier
- Competitive
- Wingman
- Casual
- Deathmatch
- FACEIT
- custom

Playlist-specific filters, analytics claims and recommendations are also not
accepted in `v0.9`.

## Docs/UI False-Claim Scan Result

Scan terms:

```text
Premier|Competitive|Wingman|Casual|Deathmatch|Faceit|FACEIT|playlist|mode
```

Runtime/UI scan scope:

- `app/web/routes.py`
- `app/templates/`
- `app/static/`

Runtime/UI findings:

- No route/template/static UI text claims Premier, Competitive, Wingman,
  Casual, Deathmatch, FACEIT or exact playlist mode as proven.
- The only runtime/UI matches were Chart.js interaction `mode`, Python model
  import text, and storage policy `current_mode`; these are not match playlist
  claims.

Docs findings:

- Historical audit/status docs contain mode and playlist discussion.
- `docs/audit/WP_016E3_CONTROLLED_COMPETITIVE_DUST2_EVALUATION_REPORT.md`
  contains the old operator-facing word `Competitive`; WP-017I/WP-017J now
  supersede that as playlist proof. The historical report was not edited or
  deleted.
- Current governance docs now carry the accepted limitation and forbid exact
  playlist claims in `v0.9`.

No severe false UI claim was found, so no runtime code was changed.

## Files Changed

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md`

## Promotion Readiness

WP-017K promotion can start: yes, if no new blocker is found.

WP-017J does not promote `v0.9`. It only removes the match-mode prerequisite by
accepting explicit deferral and limitation text.

WP-017K must carry forward:

- cap remains `1`;
- exact playlist mode is unknown/provenance-only;
- no playlist-specific claims, filters or recommendations in `v0.9`;
- root-backed storage warnings;
- `/coach` artifact overview scaling warning;
- authenticated browser timing warning;
- metadata/job-surface warnings.

## Safety Declarations

- Production DB touched: no
- Production files touched: no
- Live import/parser run: no
- Manual evaluator run: no
- Schema changed: no
- Cap changed: no
- Runtime code changed: no
- Tests changed: no
- Commit made: no

## Final Evidence

`git diff --check`:

```text
PASS (no output)
```

`python3 scripts/project_gate.py postflight`:

```text
PASS
AGENTS.md: present
docs/project_management/WP_REGISTRY.md: present
DB SHA: 2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33
```

Final DB SHA:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA unchanged: yes.
