# WP-017V Agent Workflow Report

## 1. Summary

WP-017V added a minimal repo-native agent workflow v0.1 for JC Coach. The new
workflow defines Codex working roles inside WP lifecycle: PM / Orchestrator,
Implementation, QA / Reviewer and Documentation Steward / Docs Currency Agent.

The work intentionally stays in governance/documentation only. It does not add
daemons, schedulers, background monitoring, orchestration runtime, queues or
automatic archive/delete behavior.

Result: `PASS_WITH_WARNINGS`. The warning is that this is a role workflow and
docs-currency gate, not automation. It depends on future WP prompts and reviews
actually invoking the Documentation Steward check when needed.

## 2. Preflight

- Path: `/opt/jc-coach`
- Branch: `main`
- Git status before work: clean
- Latest commits before work:
  - `b0d4a1c (HEAD -> main, origin/main) Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`
  - `e96864c Repair WP registry governance`
  - `e6b5165 Add root Codex agent contract`
  - `e17f070 Accept post-batch performance with warnings`
  - `dd5f499 Accept post-batch data integrity with warnings`

## 3. Files Changed

| Path | Reason | Summary |
|---|---|---|
| `docs/project_management/AGENT_WORKFLOW.md` | New Warm governance/process doc | Defines repo-native WP role workflow, lifecycle, Documentation Steward triggers, document update matrix, docs classification model and WP closure checklist. |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | Link operating protocol to workflow | Adds a short reference to `AGENT_WORKFLOW.md` and clarifies Documentation Steward checks are per-WP docs currency checks, not full-audit ceremony for every tiny task. |
| `docs/project_management/DOCS_INDEX.md` | Navigation update | Adds `AGENT_WORKFLOW.md` as Warm governance/process doc and explicitly keeps it out of per-task Hot context. |
| `docs/project_management/DOCS_MAP.md` | Docs map update | Adds `AGENT_WORKFLOW.md` to the Project OS layer as Warm governance reference, not Hot context. |
| `docs/project_management/WP_REGISTRY.md` | WP registration | Registers `WP-017V` as done after `WP-017U` and before planned `WP-017K`; adds it to the promotion gate prerequisites. |
| `docs/CURRENT_STATUS.md` | Minimal status update | Marks `WP-017V` as latest completed governance WP and preserves `WP-017K` as next product WP. |
| `docs/HANDOFF.md` | Minimal new-session update | Mentions `AGENT_WORKFLOW.md` as Warm governance reference and updates next safe step after WP-017V. |
| `docs/DECISIONS.md` | Durable governance decision | Records that the agent workflow is repo-native roles, not a runtime agent platform and not per-task Hot context. |
| `docs/audit/WP_017V_AGENT_WORKFLOW_REPORT.md` | WP evidence | This report. |

## 4. Agent Workflow Model

The new model is role-based:

- PM / Orchestrator Agent scopes WPs, checks clean worktree, decides Warm docs,
  assigns roles and prevents unrelated refactors.
- Implementation Agent performs scoped edits and records changed files/checks.
- QA / Reviewer Agent checks diff, acceptance, risks, forbidden changes and
  report completeness.
- Documentation Steward / Docs Currency Agent checks required docs updates and
  document currency before WP closure.

Lifecycle remains user-approved and repository-native: a request becomes a WP
only with approval, Codex executes inside scope, QA and Docs Steward checks run,
the report is written, and User/ChatGPT review happens before commit/push.

## 5. Documentation Steward Model

Documentation Steward is now an explicit role responsible for:

- Checking documentation currency after WP-level work.
- Identifying required status/navigation/canonical docs updates.
- Detecting stale entrypoints, duplicate instructions and unreferenced docs.
- Classifying docs as `CANONICAL`, `SUPPORTING`, `DRAFT`,
  `ARCHIVE_CANDIDATE` or `OBSOLETE`.
- Proposing merge/archive/deprecate actions without deleting automatically.
- Blocking WP closure when required docs or report updates are missing.

Triggers include WP closure, new canonical docs, changes to Hot/Warm docs,
promotion attempts, stale/conflicting instruction discoveries, small review
cadence after 3-5 WPs and pre-archive/deprecation work.

This role does not require a full project docs audit after every tiny task.

## 6. Docs Classification Snapshot

| File / group | Classification | Reason | Recommended action |
|---|---|---|---|
| `AGENTS.md` | `CANONICAL` | Root Codex operating contract and top active repo instruction file. | Keep current. |
| `docs/CURRENT_STATUS.md` | `CANONICAL` | Current product/runtime/blocker snapshot. | Keep current after each WP. |
| `docs/project_management/WP_REGISTRY.md` | `CANONICAL` | WP IDs, order, dependencies, statuses and report paths. | Keep current after each WP. |
| `docs/HANDOFF.md` | `CANONICAL` | Compact new-session bootstrap and next safe step. | Keep current at handoff/WP close. |
| `docs/DECISIONS.md` | `CANONICAL` | Durable process/product decisions. | Update when durable decisions are accepted. |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | `CANONICAL` | Practical operating protocol and source-of-truth hierarchy. | Keep as Warm governance reference. |
| `docs/project_management/AGENT_WORKFLOW.md` | `CANONICAL` | Defines repo-native WP role workflow and Documentation Steward closure gate. | Keep as Warm governance reference; monitor for ceremony creep. |
| `docs/project_management/MASTER_WP_CHECKLIST.md` | `SUPPORTING` | Human campaign map; registry remains canonical for status/dependencies/report paths. | Update only if campaign plan changes. |
| `docs/project_management/DOCS_INDEX.md` | `SUPPORTING` | Human navigation index; not current project state. | Keep aligned when docs roles/context levels change. |
| `docs/project_management/DOCS_MAP.md` | `CANONICAL` | Documentation ownership/source-of-truth/stale-risk map. | Keep aligned when doc roles change. |
| `AGENT.md` | `OBSOLETE` | Superseded pointer to `AGENTS.md`; must not guide work. | Keep pointer only; do not use as active contract. |
| `docs/PROJECT_OS.md` | `OBSOLETE` | Historical/superseded entrypoint with active pointer to Hot context. | Keep pointer; do not use as current state. |
| `docs/README.md` | `SUPPORTING` | Human documentation entrypoint. | Monitor and update if navigation changes materially. |
| `docs/PROJECT_GOVERNANCE.md` | `SUPPORTING` | Governance reference with useful WP/evidence policy, below newer Hot/Warm hierarchy. | Update if stale governance claims affect work. |
| Old audit reports as a group | `SUPPORTING` | Evidence/history for prior work; not current truth. | Keep; read only when task-relevant. |
| Old prompts/tasks/instructions as a group | `ARCHIVE_CANDIDATE` | Historical task specs and prompt libraries can conflict with current governance if treated as active. | Keep as evidence unless explicit archive/deprecation WP approves movement. |

## 7. What Was Intentionally Not Changed

- No application code changed.
- No DB files, schema or data changed.
- No service, nginx, systemd or deploy runtime config changed.
- No live Steam/Valve import run.
- No parser jobs run.
- No evaluator or manual evaluator jobs run.
- No product logic changed.
- No `v0.9` promotion performed.
- No WP-018 product block changed or closed.
- No archive moves, deletes or document removals performed.
- No `git add`, commit or push performed.

## 8. Risks / Remaining Gaps

- This is a role workflow, not automation.
- Documentation Steward does not automatically scan forever.
- Future optional automation can be added later if the project needs it.
- Avoid turning every tiny task into full agent ceremony.
- Existing `docs/agents/*.md` guardian docs remain domain guardrails; they are
  not runtime agents and were not rewritten in WP-017V.

## 9. Next Recommended Step

Review the WP-017V diff. If accepted, user can commit it. After that, proceed
to `WP-017K Real Data Onboarding Promotion to v0.9` or run a final short
governance consistency check if desired.

## 10. Checks

Final check results:

- `git diff --check`: PASS, no output.
- `git diff --stat`: PASS, tracked-doc diff shown:
  `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`,
  `docs/project_management/DOCS_INDEX.md`,
  `docs/project_management/DOCS_MAP.md`,
  `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`,
  `docs/project_management/WP_REGISTRY.md`; 32 insertions, 8 deletions.
  New untracked docs are visible in `git status --short`.
- `git status --short`: PASS, only WP-017V documentation changes are present.
- `python3 scripts/project_gate.py --help`: PASS, read-only help displayed
  available commands `preflight`, `changed`, `required-checks`, `postflight`.
