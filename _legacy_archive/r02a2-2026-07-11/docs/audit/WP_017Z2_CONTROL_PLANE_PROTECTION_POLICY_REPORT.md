# WP-017Z2 Control Plane Protection Policy Report

Date: 2026-07-06

## 1. Summary

WP-017Z2 added a control-plane protection policy to the repo-native agent
workflow. Control-plane docs now have explicit tiers and may be changed only by
explicit governance/control-plane tasks, except for required WP status/report
closure updates.

Ordinary product, code, DB/data, import/parser/evaluator, runtime/deploy, UI and
recommendation tasks must not modify `AGENTS.md`, workflow rules, role cards,
guardian docs or the operating protocol to make work easier. If a rule blocks a
task, Codex must stop and request approval instead of editing the rule.

## 2. Preflight

- `pwd`: `/opt/jc-coach`
- Branch: `main`
- Git status before WP-017Z2: clean
- Latest commits before WP-017Z2:
  - `e6d5cd4 (HEAD -> main) Add agent invocation and output modes`
  - `68a42a4 Promote real data onboarding to v0.9 with warnings`
  - `4b53f4b Add agent role cards and handoff protocol`
  - `5278596 Clean up legacy documentation pointers`
  - `dcb9239 (origin/main) Add legacy documentation currency snapshot`
  - `344739d Add task type profiles and prompt contract`
  - `00726c4 Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`

## 3. Files changed

| Path | Reason | Summary |
|---|---|---|
| `docs/project_management/AGENT_WORKFLOW.md` | Add protection policy. | Defines control-plane tiers, protected docs and stop/request-approval rules. |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | Short reference update. | Notes that `AGENT_WORKFLOW.md` owns control-plane protection policy. |
| `docs/agents/roles/PM_ORCHESTRATOR.md` | Routing enforcement. | PM checks whether control-plane docs are touched and authorized. |
| `docs/agents/roles/IMPLEMENTATION_AGENT.md` | Edit discipline. | Implementation blocks unauthorized control-plane edits during ordinary tasks. |
| `docs/agents/roles/QA_REVIEWER.md` | Review enforcement. | QA checks control-plane docs changed only under explicit scope. |
| `docs/agents/roles/DOCUMENTATION_STEWARD.md` | Docs closure enforcement. | Documentation Steward checks protected docs and unauthorized governance edits. |
| `docs/project_management/DOCS_INDEX.md` | Navigation update. | Adds control-plane protection to the `AGENT_WORKFLOW.md` description. |
| `docs/project_management/DOCS_MAP.md` | Navigation update. | Maps control-plane protection to the Warm workflow doc. |
| `docs/project_management/WP_REGISTRY.md` | Register WP-017Z2. | Adds WP-017Z2 as governance done before WP-018 product work. |
| `docs/CURRENT_STATUS.md` | Minimal status update. | Notes WP-017Z2 without changing product status. |
| `docs/HANDOFF.md` | Minimal handoff update. | Notes control-plane protection for future sessions. |
| `docs/DECISIONS.md` | Durable governance decision. | Records that blocked ordinary work must request approval instead of weakening rules. |
| `docs/audit/WP_017Z2_CONTROL_PLANE_PROTECTION_POLICY_REPORT.md` | WP report. | Records policy, changes, non-changes, risks and checks. |

## 4. Control-plane doc tiers

| Tier | Docs | Protection |
|---|---|---|
| Tier 0 root contract | `AGENTS.md`, `AGENT.md` pointer | Change only by explicit root-contract governance task. |
| Tier 1 workflow/control policy | `AGENT_WORKFLOW.md`, `PROJECT_OPERATING_PROTOCOL.md`, `WP_REGISTRY.md`, `CURRENT_STATUS.md`, `HANDOFF.md`, `DECISIONS.md` | Change only by explicit governance/control-plane task or required WP status/report closure update. |
| Tier 2 role and guardian behavior | `docs/agents/roles/*`, `docs/agents/*_GUARDIAN.md`, `docs/agents/README.md` | Change only by explicit role/guardian governance task. |
| Tier 3 navigation/control maps | `DOCS_INDEX.md`, `DOCS_MAP.md`, `MASTER_WP_CHECKLIST.md` | Change only when navigation, context level or campaign/control mapping changes. |

## 5. Policy behavior

- Ordinary product/code/DB/import/runtime/UI/recommendation tasks must not edit
  control-plane docs to bypass or relax rules.
- If a rule blocks a task, Codex must stop and request approval.
- Role cards, guardian docs, workflow rules and operating protocol require
  explicit governance/control-plane scope.
- Product tasks may update status docs only when explicitly required for WP
  status/report closure.
- Old prompts/audits/history do not override control-plane docs.

## 6. Role-card enforcement

- PM / Orchestrator checks whether protected docs are touched and whether scope
  authorizes that.
- Implementation blocks protected-doc edits during ordinary product work.
- QA / Reviewer checks that protected docs changed only under explicit
  governance/control-plane scope.
- Documentation Steward checks control-plane protection during docs closure.

## 7. What was intentionally not changed

- No application code changed.
- No DB/schema/data changed.
- No live Steam/Valve import ran.
- No parser/evaluator jobs ran.
- No service/nginx/deploy config changed.
- No product logic changed.
- No `v0.9` or `v0.10` product status changed.
- No WP-018 product implementation was started.
- No runtime automation, daemon, scheduler or queue was created.
- No file moves, deletes or archive moves were performed.
- No broad legacy docs cleanup was performed.
- No `git add`, commit or push was performed.

## 8. Risks / remaining gaps

- This is documentation policy, not runtime enforcement.
- Codex still needs to classify whether a requested file is control-plane before
  editing.
- Status docs remain allowed for required WP closure, so QA/Documentation
  Steward must verify the distinction between status closure and rule changes.

## 9. Next recommended step

Review and commit WP-017Z2 if accepted, then proceed to WP-018.

## 10. Checks

- `git diff --check` - PASS, no output.
- `git diff --stat` - PASS, governance/docs-only tracked diff:
  12 files changed, 84 insertions, 29 deletions. The new WP-017Z2 report is
  listed by `git status --short`.
- `git status --short` - PASS, expected docs/report changes only:
  `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`,
  `docs/agents/roles/*`, `docs/project_management/AGENT_WORKFLOW.md`,
  `docs/project_management/DOCS_INDEX.md`,
  `docs/project_management/DOCS_MAP.md`,
  `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`,
  `docs/project_management/WP_REGISTRY.md` and this report.
- `python3 scripts/project_gate.py --help` - PASS, help text displayed.
