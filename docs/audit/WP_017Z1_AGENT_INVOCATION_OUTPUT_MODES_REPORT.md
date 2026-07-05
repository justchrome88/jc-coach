# WP-017Z1 Agent Invocation Modes and File-Backed Output Contract Report

Date: 2026-07-06

## 1. Summary

WP-017Z1 added explicit invocation modes and output modes to the repo-native
agent workflow so future prompts can be shorter and safer. Generic restrictions
such as no edits, no DB mutation, no imports/parser/evaluator jobs and
file-backed output for long reviewable work are now inferred from mode, task
type and role cards.

This is governance/documentation work only. It did not change product behavior,
DB/data, runtime config or WP-018 product implementation.

## 2. Preflight

- `pwd`: `/opt/jc-coach`
- Branch: `main`
- Git status before WP-017Z1: clean
- Latest commits before WP-017Z1:
  - `68a42a4 (HEAD -> main) Promote real data onboarding to v0.9 with warnings`
  - `4b53f4b Add agent role cards and handoff protocol`
  - `5278596 Clean up legacy documentation pointers`
  - `dcb9239 (origin/main) Add legacy documentation currency snapshot`
  - `344739d Add task type profiles and prompt contract`
  - `00726c4 Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`

## 3. Files changed

| Path | Reason | Summary |
|---|---|---|
| `docs/project_management/AGENT_WORKFLOW.md` | Add mode contracts. | Added invocation modes, output modes, default file-backed rule and updated Task Card contract. |
| `docs/agents/README.md` | Navigation clarification. | Notes that `AGENT_WORKFLOW.md` owns invocation/output modes. |
| `docs/agents/roles/PM_ORCHESTRATOR.md` | Role responsibility update. | PM must choose/validate mode and output mode and request file-backed output for long planning. |
| `docs/agents/roles/IMPLEMENTATION_AGENT.md` | Safety update. | Implementation must not edit/create files in planning/review/diagnostic modes except named file-backed reports. |
| `docs/agents/roles/QA_REVIEWER.md` | Review update. | QA checks whether invocation/output mode was appropriate. |
| `docs/agents/roles/DOCUMENTATION_STEWARD.md` | Docs-audit output update. | Broad docs audits and long findings should be file-backed. |
| `docs/agents/roles/ROLE_CARD_TEMPLATE.md` | Template update. | Future role cards include mode/output considerations. |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | Short reference update. | Mentions invocation and output modes in the workflow reference. |
| `docs/project_management/DOCS_INDEX.md` | Navigation update. | Classifies `AGENT_WORKFLOW.md` as owning invocation/output modes. |
| `docs/project_management/DOCS_MAP.md` | Navigation update. | Maps invocation/output modes to the Warm workflow doc. |
| `docs/project_management/WP_REGISTRY.md` | Register WP-017Z1. | Adds WP-017Z1 as done after WP-017K and before WP-018 product work. |
| `docs/CURRENT_STATUS.md` | Minimal status update. | Notes WP-017Z1 workflow update; product status remains `v0.9`, WP-018 remains next. |
| `docs/HANDOFF.md` | Minimal handoff update. | Notes invocation/output modes for future short prompts. |
| `docs/DECISIONS.md` | Durable governance decision. | Records future prompt use of invocation/output modes and file-backed reports for long reviewable work. |
| `docs/audit/WP_017Z1_AGENT_INVOCATION_OUTPUT_MODES_REPORT.md` | WP report. | Records scope, changes, non-changes, risks and checks. |

## 4. Invocation modes added

Added modes:

- `planning-only`
- `review-only`
- `diagnostic-only`
- `implementation`
- `docs-currency`
- `WP-level`
- `approval-required`

Each mode defines whether repository files may be edited, reports may be
created, code may change, DB/data may be read or mutated, import/parser/evaluator
jobs may run, service/deploy config may change, required output and stop
conditions.

## 5. Output modes added

Added output modes:

- `console-only`: short answers only; no file creation.
- `file-backed`: long, important or reviewable output goes to exactly the
  requested report file, with compact console output.
- `patch-producing`: scoped implementation/documentation changes are allowed
  only when explicitly authorized.

Default rule: WP-level work, promotion tasks, architecture/PM planning, QA
reviews, Documentation Steward audits and outputs over about 80 lines should
prefer file-backed output. Tiny tasks do not require reports unless requested.

## 6. Prompt contract update

The Task Card now expects:

```text
Task:
Task type:
Mode:
Output mode:
Goal:
Scope, if needed:
Report path, if file-backed or WP-level:
Task-specific acceptance constraints, if needed:
Stop conditions, only if task-specific:
```

Generic restrictions come from `AGENTS.md`, task type, invocation mode, output
mode and role cards.

## 7. Role-card updates

- PM / Orchestrator: chooses or validates invocation/output mode and requests
  file-backed output for long planning.
- Implementation Agent: refuses file edits/creation in planning, review and
  diagnostic modes except an explicitly requested file-backed report.
- QA / Reviewer: checks whether the output mode matched the task and whether
  long output was file-backed.
- Documentation Steward: uses file-backed output for broad docs audits or long
  findings.
- Role Card Template: future roles must include mode/output considerations.

## 8. What was intentionally not changed

- No application code changed.
- No DB/schema/data changed.
- No live Steam/Valve import ran.
- No parser/evaluator jobs ran.
- No service/nginx/deploy config changed.
- No product logic changed.
- No `v0.9` or `v0.10` product status changed.
- No WP-018 product implementation was started.
- No file moves, deletes or archive moves were performed.
- No broad legacy docs cleanup was performed.
- No `git add`, commit or push was performed.

## 9. Risks / remaining gaps

- Invocation/output modes are documentation contracts, not runtime enforcement.
- Codex must still apply judgment when a prompt omits mode/output mode.
- File-backed planning reports should not become mandatory for tiny tasks.
- Future automation can be considered later, but WP-017Z1 intentionally adds no
  automation, daemon, scheduler or queue.

## 10. Next recommended step

Review and commit WP-017Z1 if accepted, then proceed to WP-018.

## 11. Checks

- `git diff --check` - PASS, no output.
- `git diff --stat` - PASS, governance/docs-only tracked diff:
  14 files changed, 103 insertions, 38 deletions. The new WP-017Z1 report is
  listed by `git status --short`.
- `git status --short` - PASS, expected docs/report changes only:
  `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`,
  `docs/agents/README.md`, `docs/agents/roles/*`,
  `docs/project_management/AGENT_WORKFLOW.md`,
  `docs/project_management/DOCS_INDEX.md`,
  `docs/project_management/DOCS_MAP.md`,
  `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`,
  `docs/project_management/WP_REGISTRY.md` and this report.
- `python3 scripts/project_gate.py --help` - PASS, help text displayed.
