# WP-017U Project Operating Protocol Report

## 1. Summary

WP-017U created a practical project operating protocol and a master human WP
checklist so governance, planning, blockers, reports, commits and chat/context
handoff rules are explicit before returning to WP-017K promotion review.

Result: `PASS`.

## 2. Preflight

- Working directory: `/opt/jc-coach`.
- Branch before work: `main`.
- `git status --short` before work: clean.
- Production DB SHA evidence: `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
  This was read-only evidence; WP-017U did not mutate DB/schema/data.
- Latest commits before work:
  - `17e65a6 (HEAD -> main, origin/main) Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`
  - `e96864c Repair WP registry governance`
  - `e6b5165 Add root Codex agent contract`
  - `e17f070 Accept post-batch performance with warnings`
  - `dd5f499 Accept post-batch data integrity with warnings`
  - `1b18ce9 Verify repaired pending demo import evaluation`

## 3. Files Changed

| Path | Reason | Summary |
|---|---|---|
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | New governance protocol requested by WP-017U. | Defines roles, source-of-truth hierarchy, Hot/Warm/Cold rules, WP lifecycle, document update rules, new-WP procedure, blocker procedure, report policy, commit policy, audit cadence and chat policy. |
| `docs/project_management/MASTER_WP_CHECKLIST.md` | New human-readable campaign map requested by WP-017U. | Adds the full WP checklist from WP-011D through WP-021J and states that `WP_REGISTRY.md` remains canonical. |
| `docs/project_management/DOCS_INDEX.md` | Navigation update. | Adds the new protocol/checklist and clarifies they are Warm governance/planning references, not per-task Hot context. |
| `docs/project_management/DOCS_MAP.md` | Documentation ownership/context update. | Adds the new protocol/checklist to the Project OS layer and clarifies they are not Hot context. |
| `docs/project_management/WP_REGISTRY.md` | WP registration. | Registers `WP-017U` as done after `WP-017T` and before `WP-017K`, adds its report path, and updates the promotion gate dependency. |
| `docs/CURRENT_STATUS.md` | Current state update. | Marks no active WP after WP-017U completion and keeps WP-017K as the next product WP. |
| `docs/HANDOFF.md` | New-session bootstrap update. | Points governance/planning sessions to the new Warm references and keeps WP-017K as the next safe step after review/commit. |
| `docs/DECISIONS.md` | Durable governance decision. | Records that the protocol/checklist exist and are not per-task Hot context. |
| `docs/audit/WP_017U_PROJECT_OPERATING_PROTOCOL_REPORT.md` | WP report. | Records WP-017U result, evidence, changed files, non-changes, checks, risks and next step. |

## 4. Operating Model

- User is approval authority, commit authority and product owner.
- ChatGPT PM is the planning/review/decision-support layer.
- Codex CLI is the executor/auditor/file updater.
- Repository docs are the accepted source of truth; Git is immutable technical
  history after user-approved commits.
- Source-of-truth hierarchy is now explicit: `AGENTS.md`,
  `CURRENT_STATUS.md`, `WP_REGISTRY.md`, `HANDOFF.md`, `DECISIONS.md`, then
  Warm domain docs, then evidence/history, then chat messages only after they
  are written into repository docs.
- WP lifecycle now documents `planned`, `active`, `done`, `blocked`,
  `deferred`, `failed`, `superseded` and `out-of-band evidence`.
- Document update rules now specify when to update status, registry, handoff,
  decisions, checklist, docs navigation, audit reports and domain docs.

## 5. Checklist Model

`MASTER_WP_CHECKLIST.md` is a human-readable campaign map for planning and
audit. It is not per-task Hot context. `WP_REGISTRY.md` remains canonical for
WP status, dependencies and report paths. If the checklist and registry
conflict, the registry wins until the checklist is reconciled.

## 6. What Was Intentionally Not Changed

- No application code changed.
- No DB, schema or data changed.
- No service, nginx or deploy runtime config changed.
- No live Steam/Valve import run.
- No parser jobs run.
- No evaluator or manual evaluator jobs run.
- No product logic changed.
- No `v0.9` promotion performed.
- No planned WP-018 product block changed.
- No archive moves, document moves or document deletes performed.
- No `git add`, commit or push performed.

## 7. Next Recommended Step

1. Review the WP-017U diff.
2. Commit if accepted.
3. Optionally run one final governance consistency check.
4. Proceed to `WP-017K Real Data Onboarding Promotion to v0.9` only with
   explicit user/ChatGPT approval.

## 8. Checks

Required final checks were run:

- `git diff --check`: PASS, no output.
- `git diff --stat`: docs-only tracked diff at check time:
  - `docs/CURRENT_STATUS.md`: 6 changed lines.
  - `docs/DECISIONS.md`: 1 added line.
  - `docs/HANDOFF.md`: 10 changed lines.
  - `docs/project_management/DOCS_INDEX.md`: 15 changed lines.
  - `docs/project_management/DOCS_MAP.md`: 17 changed lines.
  - `docs/project_management/WP_REGISTRY.md`: 9 changed lines.
- `git status --short`: only allowed governance/documentation files are
  modified or untracked.
- `python3 scripts/project_gate.py --help`: PASS; command displayed read-only
  help for `preflight`, `changed`, `required-checks` and `postflight`.

No tests were run because WP-017U is governance/documentation-only and the
prompt requested no tests unless known read-only and non-mutating.
