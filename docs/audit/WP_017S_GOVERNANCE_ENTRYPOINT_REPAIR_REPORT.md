# WP-017S Governance Entrypoint Repair Report

Date: 2026-07-05.

## 1. Summary

WP-017S repaired the documentation governance entrypoints before the WP-017K
promotion lane continues. The pass did not change product code or runtime
behavior.

Changed:

- `AGENTS.md` is now explicitly the only root Codex operating contract.
- `AGENT.md` is now a short superseded pointer to `AGENTS.md`.
- Stale entrypoint/navigation docs no longer present old `v0.4.1`, `v0.5`,
  `WP-012` or `WP-014` values as current project state.
- Hot/Warm/Cold context policy is documented.
- Old audit reports, old prompts, stage reports and generated data reports are
  explicitly evidence/history and cannot override current control docs.
- `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is explicitly
  treated as out-of-band governance audit evidence and does not consume the
  planned `WP-018` product ID.

Why:

- The WP-018 documentation governance audit found entrypoint drift and excessive
  mandatory reading risk. WP-017S fixes the highest-risk entrypoints without a
  physical archive move or broad documentation rewrite.

## 2. Preflight state

Branch:

```text
main
```

Latest commits:

```text
6514c80 (HEAD -> main) Diagnose match mode classification limits
e96864c Repair WP registry governance
e6b5165 Add root Codex agent contract
e17f070 (origin/main) Accept post-batch performance with warnings
dd5f499 Accept post-batch data integrity with warnings
1b18ce9 Verify repaired pending demo import evaluation
41a7c5e Repair Steam import recommendation evaluation timing
6bb4c56 Diagnose post-batch evaluation trigger
```

Git status before WP-017S edits:

```text
 M docs/CURRENT_STATUS.md
 M docs/HANDOFF.md
 M docs/PROJECT_CONTROL.md
 M docs/project_management/ACCEPTANCE_MATRIX.md
 M docs/project_management/VERSION_ROADMAP.md
 M docs/project_management/WORK_PACKAGE_BACKLOG.md
 M docs/project_management/WP_REGISTRY.md
?? docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md
?? docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md
```

Pre-existing dirty files:

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md`
- `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md`

WP-017S worked with the dirty tree and did not revert or stage pre-existing
changes.

## 3. Files changed

| Path | Reason | Summary |
|---|---|---|
| `AGENTS.md` | Make it the sole Codex contract and add context economy rules. | Added only-root-contract wording, Hot/Warm/Cold reading policy, no `git add`/commit/push without approval, file-report rule, and blocker/WP safety rules. |
| `AGENT.md` | Supersede stale agent rules without deleting the file. | Replaced old mandatory-heavy rules with a short pointer to `AGENTS.md` and Hot context. |
| `docs/PROJECT_OS.md` | Remove stale current-state claims. | Added historical/superseded status block, replaced fixed old version/WP with references to current control docs, and documented Hot/Warm reading policy. |
| `docs/README.md` | Repair navigation entrypoint. | Added navigation status block, replaced stale WP-012 target with links to current truth, and clarified that Hot context overrides historical evidence. |
| `docs/project_management/DOCS_INDEX.md` | Repair navigation and context classification. | Added Hot/Warm/Cold section, marked `AGENT.md` superseded, marked `PROJECT_OS.md` historical/superseded, and removed stale current WP claim. |
| `docs/project_management/DOCS_MAP.md` | Repair ownership map. | Added context policy, changed active agent contract from `AGENT.md` to `AGENTS.md`, marked `PROJECT_OS.md` superseded, and documented the out-of-band WP_018 audit report. |
| `docs/PROJECT_GOVERNANCE.md` | Remove stale current version/WP claims. | Added status block, replaced fixed current `v0.4.1`/`WP-012` claims with links to current control docs, and added `v0.10` Coach Quality Calibration to the version map. |
| `docs/project_management/WP_REGISTRY.md` | Avoid silent WP numbering conflict and record WP-017S. | Added note that `WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is out-of-band evidence, added `WP-017S` before `WP-017K`, and made `WP-017S` a WP-017K prerequisite. |
| `docs/audit/WP_017S_GOVERNANCE_ENTRYPOINT_REPAIR_REPORT.md` | Required audit report. | Created this report. |

## 4. Source-of-truth model after repair

Per-task Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

New-session Hot context:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`
4. `docs/HANDOFF.md`

Warm context:

- Roadmap/planning: `VERSION_ROADMAP.md`, `WORK_PACKAGE_BACKLOG.md`.
- Acceptance/promotion: `ACCEPTANCE_MATRIX.md`, relevant current WP reports.
- Deploy/service: `DEPLOYMENT.md`, deploy refs, `RUNTIME_GUARDIAN`.
- Testing/gates: `TESTING.md`, `TEST_GUARDIAN`, `scripts/project_gate.py`.
- DB/data integrity: `BACKUP_RESTORE.md`, `MIGRATIONS.md`, `DB_GUARDIAN`.
- Import/parser/evaluator: `STEAM_IMPORT.md`, `DEMO_STORAGE_TZ.md`,
  `DEMO_DEEP_PARSER_TZ_RU`, `IMPORT_GUARDIAN`, relevant recent audit reports.
- Recommendations: `RECOMMENDATIONS.md`, `METRICS.md`, `METRICS_GUARDIAN`.
- UI/web routes: `UI_COACH_GUARDIAN`, relevant route/template/static files.
- Security: `SECURITY.md`, release/public deployment checklists.
- Historical WP review: only reports needed by the active investigation.

Before reading Warm docs, Codex should state which files are needed and why.

Cold/evidence context:

- Old audit reports and stage reports.
- Old prompts.
- `docs/tasks/*`.
- `instructions/*`.
- Old roadmap/version docs.
- Generated data reports and AI handoffs.

Cold context is evidence/history only and must not override Hot context.

## 5. WP-018 naming conflict handling

The file `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` exists
because the earlier audit was saved under that requested path. This repair pass
does not consume, rename or replace the planned `WP-018` product block.

`docs/project_management/WP_REGISTRY.md` now explicitly states that
`WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is out-of-band governance
audit evidence and does not consume or replace the planned `WP-018` product
work-package ID.

No silent WP renumbering was performed.

The actual repair pass is registered as `WP-017S Documentation Governance
Entrypoint Repair`.

## 6. What was intentionally not changed

- No product code changed.
- No DB/schema/data changed.
- No systemd service or nginx config changed.
- No live Steam/Valve import ran.
- No parser job ran.
- No manual evaluator ran.
- No import/parser/evaluator/recommendation/UI logic changed.
- No physical archive moves were performed.
- No documents were deleted.
- No `scripts/project_gate.py` changes were made.
- No `v0.9` promotion was performed.
- No planned `WP-018` product block changes were made.
- No `git add`, commit or push was performed.
- `docs/PROJECT_CONTROL.md`, `docs/DECISIONS.md`, `docs/ROADMAP.md`,
  `docs/VERSION_MAP.md`, `WORKLOG.md`, `docs/tasks/*`, `instructions/*` and old
  audit reports were intentionally not repaired in this pass.

## 7. Recommended next pass

Recommended next safe governance pass:

1. Compress `docs/CURRENT_STATUS.md` so it remains Hot but does not carry full
   history.
2. Compress `docs/HANDOFF.md` to immediate continuation state, next WP and
   recent warnings.
3. Update `docs/DECISIONS.md` with recent decisions: root `AGENTS.md`,
   WP registry, mode deferral, cap `1`, no playlist claims in `v0.9`.
4. Decide whether a new `CURRENT_STATE.md` or `NEXT_ACTIONS.md` is still needed
   after compression. Prefer not to create new docs if existing docs can carry
   the role cleanly.
5. Optionally add non-mutating freshness checks to `scripts/project_gate.py` in
   a later explicit tooling WP.

## 8. Checks

Safe checks requested and run:

```text
git diff --stat
git status --short
python scripts/project_gate.py --help
```

`git diff --stat`:

```text
AGENT.md                                        | 61 ++++---------------------
AGENTS.md                                       | 40 +++++++++++++++-
docs/CURRENT_STATUS.md                          |  5 +-
docs/HANDOFF.md                                 | 10 ++--
docs/PROJECT_CONTROL.md                         |  7 +--
docs/PROJECT_GOVERNANCE.md                      | 13 ++++--
docs/PROJECT_OS.md                              | 41 +++++++++++------
docs/README.md                                  | 46 ++++++++++---------
docs/project_management/ACCEPTANCE_MATRIX.md    |  2 +-
docs/project_management/DOCS_INDEX.md           | 41 +++++++++++++----
docs/project_management/DOCS_MAP.md             | 23 ++++++++--
docs/project_management/VERSION_ROADMAP.md      |  6 +--
docs/project_management/WORK_PACKAGE_BACKLOG.md | 12 ++---
docs/project_management/WP_REGISTRY.md          | 26 ++++++++---
14 files changed, 202 insertions(+), 131 deletions(-)
```

Note: this stat includes pre-existing WP-017J documentation changes that were
already dirty before WP-017S started.

`git status --short`:

```text
 M AGENT.md
 M AGENTS.md
 M docs/CURRENT_STATUS.md
 M docs/HANDOFF.md
 M docs/PROJECT_CONTROL.md
 M docs/PROJECT_GOVERNANCE.md
 M docs/PROJECT_OS.md
 M docs/README.md
 M docs/project_management/ACCEPTANCE_MATRIX.md
 M docs/project_management/DOCS_INDEX.md
 M docs/project_management/DOCS_MAP.md
 M docs/project_management/VERSION_ROADMAP.md
 M docs/project_management/WORK_PACKAGE_BACKLOG.md
 M docs/project_management/WP_REGISTRY.md
?? docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md
?? docs/audit/WP_017S_GOVERNANCE_ENTRYPOINT_REPAIR_REPORT.md
?? docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md
```

`python3 scripts/project_gate.py --help`:

```text
usage: project_gate.py [-h] {preflight,changed,required-checks,postflight} ...

Read-only project governance gate.
```
