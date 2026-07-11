# WP-017W Task Type Profiles and Prompt Contract Report

## 1. Summary

WP-017W completed the repo-native workflow layer by adding task type routing,
role invocation shortcuts, a standard Task Card prompt contract, standard WP
preflight and standard WP console output guidance to
`docs/project_management/AGENT_WORKFLOW.md`.

The goal is to let future prompts stay short: task-specific prompts can name
task type, scope, allowed/forbidden changes and stop conditions while generic
workflow rules remain in `AGENTS.md` and `AGENT_WORKFLOW.md`.

Result: `PASS_WITH_WARNINGS`. The warning is ceremony creep risk: the profiles
are guidance for routing work, not a reason to force full WP process onto every
tiny task.

## 2. Preflight

- Path: `/opt/jc-coach`
- Branch: `main`
- Git status before work: clean
- Latest commits before work:
  - `00726c4 (HEAD -> main, origin/main) Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`
  - `e96864c Repair WP registry governance`
  - `e6b5165 Add root Codex agent contract`
  - `e17f070 Accept post-batch performance with warnings`

## 3. Files Changed

| Path | Reason | Summary |
|---|---|---|
| `docs/project_management/AGENT_WORKFLOW.md` | Main WP-017W deliverable | Adds task type profiles, role invocation shortcuts, Task Card contract, standard WP preflight, standard output contract and Documentation Steward standalone mode. |
| `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` | Operating protocol link | Adds short references to task routing, role shortcuts and Task Card contract without duplicating workflow content. |
| `AGENTS.md` | Root contract pointer | Adds a short pointer to `AGENT_WORKFLOW.md` for task routing and prompt/report contracts; Hot context is unchanged. |
| `docs/project_management/DOCS_INDEX.md` | Navigation update | Clarifies that `AGENT_WORKFLOW.md` includes task type profiles and prompt contract and remains Warm governance context. |
| `docs/project_management/DOCS_MAP.md` | Docs map update | Updates the `AGENT_WORKFLOW.md` role description and Warm-context wording. |
| `docs/project_management/WP_REGISTRY.md` | WP registration | Registers `WP-017W` as done after `WP-017V` and before planned `WP-017K`. |
| `docs/CURRENT_STATUS.md` | Minimal status update | Marks `WP-017W` as latest completed governance WP and preserves `WP-017K` as next product WP. |
| `docs/HANDOFF.md` | Minimal handoff update | Mentions task routing and Task Card workflow as Warm governance context and preserves WP-017K as next product WP. |
| `docs/DECISIONS.md` | Durable governance decision | Records that future prompts should use Task Card plus task type profiles instead of repeating generic workflow instructions. |
| `docs/audit/WP_017W_TASK_TYPE_PROFILES_PROMPT_CONTRACT_REPORT.md` | WP evidence | This report. |

## 4. Task Type Profiles Added

Profiles added to `AGENT_WORKFLOW.md`:

- Tiny task.
- Scoped implementation task.
- WP-level implementation task.
- Promotion / acceptance task.
- Diagnostic / investigation task.
- Documentation / governance task.
- Docs currency check.
- DB / data task.
- Import / parser / evaluator task.
- Deploy / runtime task.
- UI / web task.
- Recommendations / coach quality task.

Each profile states expected roles, when Documentation Steward is required,
what Warm docs are needed by category and which mutations require explicit
authorization.

## 5. Prompt Contract

Standard Task Card:

```text
Task:
Task type:
Goal:
Scope:
Allowed changes:
Forbidden changes:
Task-specific acceptance constraints:
Report path, if WP-level:
Stop conditions:
```

Generic rules should come from `AGENTS.md` and
`docs/project_management/AGENT_WORKFLOW.md`; future prompts should not repeat
the full workflow unless a task needs stricter constraints.

## 6. Documentation Steward Standalone Mode

Standalone invocation format:

```text
Invoke Documentation Steward.
Mode: targeted docs currency check.
Scope: governance docs.
Do not edit files.
Output: findings, classifications, recommended minimal actions.
```

Required output includes checked scope, classifications, stale/conflicting docs,
duplicate instructions, unreferenced docs if checked, required updates,
recommended actions and confirmation that no automatic deletion occurred.

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

- This is still repo-native role routing, not autonomous runtime.
- Optional future automation can be added later only if needed.
- Avoid ceremony creep: tiny tasks should stay tiny.
- The Task Card reduces prompt length only if future prompts rely on it instead
  of restating generic governance rules.

## 9. Next Recommended Step

Review the WP-017W diff. If accepted, commit it. Then proceed to
`WP-017K Real Data Onboarding Promotion to v0.9`.

## 10. Checks

Final check results:

- `git diff --check`: PASS, no output.
- `git diff --stat`: PASS, tracked-doc diff shown:
  `AGENTS.md`, `docs/CURRENT_STATUS.md`, `docs/DECISIONS.md`,
  `docs/HANDOFF.md`, `docs/project_management/AGENT_WORKFLOW.md`,
  `docs/project_management/DOCS_INDEX.md`,
  `docs/project_management/DOCS_MAP.md`,
  `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`,
  `docs/project_management/WP_REGISTRY.md`; 210 insertions, 18 deletions.
  New untracked WP report is visible in `git status --short`.
- `git status --short`: PASS, only WP-017W documentation changes are present.
- `python3 scripts/project_gate.py --help`: PASS, read-only help displayed
  available commands `preflight`, `changed`, `required-checks`, `postflight`.
