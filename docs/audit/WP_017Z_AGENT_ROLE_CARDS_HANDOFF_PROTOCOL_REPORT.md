# WP-017Z Agent Role Cards and Role Handoff Protocol Report

## 1. Summary

WP-017Z made the repo-native agent workflow more explicit by adding Warm role
cards for the four core workflow roles and a short role handoff protocol in
`docs/project_management/AGENT_WORKFLOW.md`.

This is documentation/governance work only. The role cards are behavior
contracts for Codex inside WP work. They are not runtime agents, daemons,
schedulers, queues or automation.

## 2. Preflight

- `pwd`: `/opt/jc-coach`
- Branch: `main`
- Git status before: clean
- Latest commits before work:
  - `5278596 (HEAD -> main) Clean up legacy documentation pointers`
  - `dcb9239 (origin/main) Add legacy documentation currency snapshot`
  - `344739d Add task type profiles and prompt contract`
  - `00726c4 Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`

## 3. Files changed

| Path | Reason | Summary |
|---|---|---|
| `docs/agents/README.md` | New role/guardian index. | Distinguishes workflow role cards, existing domain guardian docs and the existing supporting `docs/agents/PM_ORCHESTRATOR.md`; confirms role cards are Warm context only. |
| `docs/agents/roles/PM_ORCHESTRATOR.md` | New PM / Orchestrator role card. | Defines task routing, scope, Warm docs selection, stop conditions, blocker handling and handoffs. |
| `docs/agents/roles/IMPLEMENTATION_AGENT.md` | New Implementation role card. | Defines scoped edit discipline, forbidden domains, changed-files reporting and QA handoff. |
| `docs/agents/roles/QA_REVIEWER.md` | New QA / Reviewer role card. | Defines diff review, acceptance checks, forbidden-change checks, report completeness and verdicts. |
| `docs/agents/roles/DOCUMENTATION_STEWARD.md` | New Documentation Steward role card. | Defines docs currency checks, source-of-truth hierarchy, classifications, closure readiness and standalone output. |
| `docs/agents/roles/ROLE_CARD_TEMPLATE.md` | Template for future approved roles. | Provides the required role-card sections and future role checklist. |
| `docs/project_management/AGENT_WORKFLOW.md` | Link role cards and define handoff protocol. | Adds role-card pointers and a role handoff protocol while keeping this file the workflow router. |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | Short operating protocol reference. | Notes that role behavior contracts live under `docs/agents/roles/` as Warm role definitions. |
| `docs/project_management/DOCS_INDEX.md` | Navigation update. | Adds the role cards and clarifies guardian docs remain supporting domain guardrails. |
| `docs/project_management/DOCS_MAP.md` | Navigation/status map update. | Classifies role cards as Warm role definitions and guardian docs as supporting domain guardrails. |
| `docs/project_management/WP_REGISTRY.md` | Register WP-017Z. | Adds WP-017Z as done after WP-017Y and before planned WP-017K. |
| `docs/CURRENT_STATUS.md` | Minimal current-state update. | Marks WP-017Z as latest completed governance WP and keeps WP-017K as next product WP. |
| `docs/HANDOFF.md` | Minimal new-session update. | Mentions role cards/handoff protocol and keeps WP-017K as next product WP. |
| `docs/DECISIONS.md` | Durable governance decision. | Records that agent behavior is controlled by `AGENT_WORKFLOW.md` plus Warm role cards; new roles require explicit approval. |
| `docs/audit/WP_017Z_AGENT_ROLE_CARDS_HANDOFF_PROTOCOL_REPORT.md` | WP report. | Records scope, changes, non-changes, risks, next step and checks. |

## 4. Role cards created

- PM / Orchestrator: detects task type, defines scope, selects Warm docs, sets
  stop conditions and routes work to the right roles.
- Implementation Agent: makes only scoped, authorized edits and reports changed
  files, checks, intentional non-changes and risks.
- QA / Reviewer: checks diff against scope, acceptance criteria, forbidden
  changes, checks evidence, report completeness and verdict.
- Documentation Steward: checks documentation currency, source-of-truth
  hierarchy, required doc updates, classifications and closure readiness.
- Role Card Template: standard section set and checklist for future approved
  role additions.

## 5. Role handoff protocol

The handoff protocol is now explicit in `AGENT_WORKFLOW.md`:

- PM / Orchestrator -> Implementation: scope, allowed files, forbidden zones,
  required checks and stop conditions.
- Implementation -> QA / Reviewer: changed files, summary, checks run,
  intentional non-changes and risks.
- QA / Reviewer -> Documentation Steward: whether docs/status/source-of-truth
  changed and which docs closure checks are required.
- Documentation Steward -> PM / Orchestrator / User: closure verdict, missing
  docs, stale docs and required user decisions.
- Any role -> User: blocker, approval request or unsafe action warning.

No role may run `git add`, commit or push. No role may expand scope without
PM/User approval. No role may treat old prompts/audits as current truth.

## 6. docs/agents organization

`docs/agents/roles/` now contains workflow role cards. These are Warm role
definitions and are read only when the role is invoked or the task type
requires them.

`docs/agents/*_GUARDIAN.md` files remain supporting domain guardrails for DB,
runtime, test, import/parser, metrics and UI boundaries.

`docs/agents/PM_ORCHESTRATOR.md` remains an existing supporting PM/domain
guardrail. The canonical PM workflow role card is
`docs/agents/roles/PM_ORCHESTRATOR.md`.

`AGENT_WORKFLOW.md` remains the workflow router, and
`PROJECT_OPERATING_PROTOCOL.md` remains the operating policy.

## 7. What was intentionally not changed

- No code changed.
- No DB, schema or data changed.
- No service, nginx or deploy runtime config changed.
- No live import, parser or evaluator jobs ran.
- No product logic changed.
- No `v0.9` promotion was performed.
- No planned WP-018 product block changes were made.
- No file moves, deletes or archive moves were performed.
- No broad legacy documentation cleanup was performed.
- No document archive manifest or broad document registry was created.
- No `git add`, commit or push was performed.

## 8. Risks / remaining gaps

- Role cards are repo-native guidance, not runtime agents.
- Future specialized roles can be added only if needed and explicitly approved.
- Avoid ceremony creep: tiny tasks should still use the light task profile.
- Physical legacy docs cleanup remains deferred and is not part of WP-017Z.

## 9. Next recommended step

Commit WP-017Z if accepted, then proceed to WP-017K.

## 10. Checks

- `git diff --check` - PASS, no output.
- `git diff --stat` - PASS, governance/status/doc-map diff only:
  8 tracked files changed, 93 insertions, 29 deletions; new untracked role-card
  and report files are listed by `git status --short`.
- `git status --short` - PASS, expected docs-only modified/untracked files:
  `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`,
  `docs/project_management/AGENT_WORKFLOW.md`,
  `docs/project_management/DOCS_INDEX.md`,
  `docs/project_management/DOCS_MAP.md`,
  `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`,
  `docs/project_management/WP_REGISTRY.md`, `docs/agents/README.md`,
  `docs/agents/roles/*` and this report.
- `python3 scripts/project_gate.py --help` - PASS, help text displayed.
