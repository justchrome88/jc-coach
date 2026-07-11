# WP-017K Real Data Onboarding Promotion Report

Date: 2026-07-06

## 1. Result

`PASS_WITH_WARNINGS`

Real Data Onboarding / Bulk Demo Usage is promoted to `v0.9` for controlled
personal use.

The promotion is honest only with the warnings carried forward below. WP-017K
does not authorize a Steam import cap raise, playlist-specific mode claims,
friends/public readiness, DB/schema changes, service changes or product logic
changes.

## 2. Preflight

- `pwd`: `/opt/jc-coach`
- Branch: `main`
- Git status before WP-017K: clean
- Latest commits before WP-017K:
  - `4b53f4b (HEAD -> main) Add agent role cards and handoff protocol`
  - `5278596 Clean up legacy documentation pointers`
  - `dcb9239 (origin/main) Add legacy documentation currency snapshot`
  - `344739d Add task type profiles and prompt contract`
  - `00726c4 Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`

## 3. Scope

Promotion readiness review and required documentation/status updates only.

No application code, DB/schema/data, import/parser/evaluator, service/nginx,
deploy runtime config or product logic changes were in scope.

## 4. Evidence reviewed

| Evidence | Promotion relevance |
|---|---|
| `docs/CURRENT_STATUS.md` | Current product state, next WP, accepted limitations and current DB SHA. |
| `docs/project_management/WP_REGISTRY.md` | Canonical WP order, prerequisites and WP-017K promotion gate. |
| `docs/project_management/ACCEPTANCE_MATRIX.md` | Acceptance criteria and current v0.9 feature row. |
| `docs/project_management/VERSION_ROADMAP.md` | Version sequence and v0.9/v0.10 transition. |
| `docs/KNOWN_LIMITATIONS.md` | Limitations that must remain visible after promotion. |
| `docs/audit/WP_017G_POST_BATCH_DATA_INTEGRITY_ACCEPTANCE_REPORT.md` | Data integrity accepted with warnings. |
| `docs/audit/WP_017H_POST_BATCH_PERFORMANCE_ACCEPTANCE_REPORT.md` | Performance accepted with warnings at current data volume. |
| `docs/audit/WP_017I_MATCH_MODE_CLASSIFICATION_DIAGNOSIS_REPORT.md` | Exact playlist mode not recoverable from current persisted data. |
| `docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md` | Exact playlist-mode limitation accepted for `v0.9`. |
| `docs/audit/WP_017Z_AGENT_ROLE_CARDS_HANDOFF_PROTOCOL_REPORT.md` | Governance prerequisite completed before promotion. |

Read-only DB SHA evidence:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

## 5. Accepted v0.9 scope

Accepted for controlled personal use:

- 76 total matches.
- 22 playable demo matches.
- 20 exact playable dates.
- 22 parser artifacts.
- Exact-date imported matches `#75` and `#76`.
- Recommendation `#5` has three evaluations with `metric_confidence`.
- Recommendation `#5` progress is `3/10`.
- One-demo-capped import/onboarding path has accepted data integrity and
  performance evidence with warnings.

## 6. Warnings carried forward

- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1`; no cap raise is accepted.
- Match playlist mode is not accepted as exact in `v0.9`.
- Current data can distinguish parser/import provenance (`demo`) and generic
  Valve share-code provenance (`Valve Matchmaking`), but not Premier,
  Competitive, Wingman, Casual, Deathmatch, FACEIT or custom modes.
- No playlist-specific claims, filters or recommendations are accepted in
  `v0.9` unless a future WP captures reliable mode metadata.
- Authenticated owner-browser timing remains unavailable from Codex evidence.
- `/coach` artifact overview is acceptable at 22 demos but should be optimized
  before materially larger demo volume.
- Historical queued non-parent Steam jobs `#1` and `#10` remain.
- Raw demos and manual backups remain on root-backed storage.
- 15 historical retained demo files remain unreferenced by current match or
  parser artifact paths.
- Friends/public readiness remains blocked.

## 7. Promotion decision

`v0.9` is promoted with warnings.

Reasoning:

- Required registry prerequisites through WP-017Z are complete.
- WP-017G accepted data integrity with warnings.
- WP-017H accepted performance with warnings for the current 22-demo data
  volume.
- WP-017I diagnosed exact playlist mode as unrecoverable from current persisted
  data.
- WP-017J accepted explicit deferral and limitation text, so playlist mode does
  not block `v0.9` as long as `v0.9` does not claim playlist-specific features.
- Current warnings are bounded and visible in status docs.

## 8. Files changed

| Path | Reason | Summary |
|---|---|---|
| `docs/CURRENT_STATUS.md` | Promotion status update. | Product version is now `v0.9`; WP-018 is next; warnings carried forward. |
| `docs/HANDOFF.md` | New-session bootstrap update. | Handoff now starts from promoted `v0.9` and points to WP-018. |
| `docs/project_management/WP_REGISTRY.md` | Canonical WP status update. | WP-017K marked `done`; report path added; WP-018 dependency updated to WP-017K promotion. |
| `docs/project_management/VERSION_ROADMAP.md` | Version roadmap update. | `v0.9` marked completed/promoted with warnings; next active target is `v0.10`. |
| `docs/project_management/ACCEPTANCE_MATRIX.md` | Acceptance state update. | Real data onboarding row now records promoted-with-warnings scope and constraints. |
| `docs/KNOWN_LIMITATIONS.md` | Limitation visibility. | Adds v0.9 warning set for cap, playlist mode, browser timing, `/coach` scaling and queued jobs. |
| `docs/DECISIONS.md` | Durable promotion decision. | Records `v0.9` promoted with warnings and no friends/public readiness claim. |
| `docs/audit/WP_017K_REAL_DATA_ONBOARDING_PROMOTION_REPORT.md` | WP report. | Records promotion decision, evidence, warnings, safety and next WP. |

## 9. What was intentionally not changed

- No application code changed.
- No DB/schema/data mutation was performed.
- No live Steam/Valve import ran.
- No parser jobs ran.
- No evaluator or manual evaluator jobs ran.
- No service/nginx/deploy runtime config changed.
- No product logic changed.
- No WP-018 product block changes were made beyond pointing next work to the
  already planned WP-018.
- No cap raise was made.
- No demo files were deleted, moved or compressed.
- No `git add`, commit or push was performed.

## 10. QA / Reviewer verdict

`PASS_WITH_WARNINGS`

Acceptance criteria are met for a bounded `v0.9` promotion. The warnings are
explicit and must remain visible. No forbidden change was detected in scope.

## 11. Documentation Steward closure

Required docs updated:

- `docs/project_management/WP_REGISTRY.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/DECISIONS.md`
- this WP report

Closure verdict: `PASS_WITH_WARNINGS`.

## 12. Next WP

`WP-018 Coach Quality Calibration`.

## 13. Checks

- `git diff --check` - PASS, no output.
- `git diff --stat` - PASS, tracked docs-only diff:
  7 files changed, 49 insertions, 28 deletions. The untracked WP-017K report is
  listed by `git status --short`.
- `git status --short` - PASS, expected docs/report changes only:
  `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`,
  `docs/KNOWN_LIMITATIONS.md`,
  `docs/project_management/ACCEPTANCE_MATRIX.md`,
  `docs/project_management/VERSION_ROADMAP.md`,
  `docs/project_management/WP_REGISTRY.md` and this report.
- `python3 scripts/project_gate.py --help` - PASS, help text displayed.
- `python3 scripts/project_gate.py preflight` - PASS, read-only governance gate
  displayed current dirty docs status, DB SHA and service status.
- `sha256sum data/cs2_coach.db` - PASS, DB SHA matches WP-017H/WP-017J:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
