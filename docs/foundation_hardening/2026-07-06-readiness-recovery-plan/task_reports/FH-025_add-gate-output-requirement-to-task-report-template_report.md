# FH-025 Add Gate Output Requirement To Task Report Template

Date: 2026-07-07

## Result

Verdict: PASS_WITH_WARNINGS

The scoped reporting-contract update is complete. Required docs-safe checks
passed. Verdict is `PASS_WITH_WARNINGS` because the known full-suite pytest
stall remains an open pre-existing residual quality-gate risk and final
readiness is not claimed.

## Scope

Updated the standard Executor reporting contract so WP-level, hardening and
file-backed Executor reports require reviewable gate output evidence for every
required check.

No product behavior, scripts, tests, CI provider configuration, status docs, DB
files, runtime/service config or generated data were changed.

## Files Changed

- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-025_add-gate-output-requirement-to-task-report-template_report.md`

## Diff Summary

- `AGENT_WORKFLOW.md` now requires each report checks evidence section to
  include command, result status and relevant output excerpt or artifact/log
  path for each required check.
- `AGENT_WORKFLOW.md` now states that long output may be summarized, but a bare
  "passed" statement is insufficient for PM review.
- `AGENT_WORKFLOW.md` now states that code/script/test tasks may use
  `.venv/bin/python scripts/local_quality_gate.py` output as covering evidence
  for project gate subcommands, full safe pytest, Ruff and `git diff --check`,
  unless the Task Card asks for separate output.
- `AGENT_WORKFLOW.md` preserves practical docs-only expectations: docs-only
  governance/status/report tasks use docs-safe project gate commands,
  `git diff --check`, scope/allowed-file review and task-specific checks unless
  the Task Card or changed files require pytest, Ruff or the local quality gate.
- `07_CODEX_EXECUTION_HANDOFF.md` now includes the gate output evidence
  requirement in strict rules, definition of done and the standard report
  shape.

Postflight diff stat:

```text
.../07_CODEX_EXECUTION_HANDOFF.md                  | 23 ++++++++++++--
docs/project_management/AGENT_WORKFLOW.md          | 35 ++++++++++++++--------
2 files changed, 43 insertions(+), 15 deletions(-)
```

## Gate Output Requirement Summary

Future WP-level, hardening and file-backed Executor reports must include, for
each required check:

- command;
- result status;
- relevant output excerpt or artifact/log path;
- exact reason and task authorization status if not run;
- exact failure, stall or timeout summary plus residual risk, owner and target
  follow-up when relevant.

Long command output may be summarized, but the report must include enough
concrete output or artifact/log pointers for PM review to verify the claim.

## Mandatory PASS Policy Summary

FH-024 mandatory PASS policy is preserved:

- `PASS` requires every required check for the task/change class and Task Card
  to pass, unless the Task Card explicitly authorizes a narrower check set.
- Missing, failed, stalled, timed-out or unauthorized skipped required checks
  block `PASS`.
- `PASS_WITH_WARNINGS` cannot stand in for a failed mandatory gate.
- Completed scoped work with failed required checks uses `FAIL`; unsafe or
  unavailable required checks use `BLOCKED`.

The documentation does not claim hosted CI exists, does not claim final
readiness, and does not claim the known full-suite pytest stall is fixed.

## Docs Update Checklist

- Hot/current status docs: checked; no update required. FH-025 is a scoped
  report-template/reporting-contract change and the Task Card forbids editing
  `docs/CURRENT_STATUS.md`.
- WP registry/status/handoff docs: checked and updated where allowed.
  `07_CODEX_EXECUTION_HANDOFF.md` was in scope and updated. `WP_REGISTRY.md`
  and `HANDOFF.md` were checked as Hot/new-session context but not edited
  because FH-025 does not change WP status and the Task Card forbids status doc
  edits.
- Navigation docs: checked; no update required. No new canonical navigation
  target was introduced; the report is at the Task Card path.
- Task-relevant domain docs: checked and updated. The relevant governance
  contract docs are `AGENT_WORKFLOW.md` and `07_CODEX_EXECUTION_HANDOFF.md`.
- Documentation Steward: completed for this scoped docs task via changed-file,
  Hot/current status, navigation, task-relevant docs and control-plane-scope
  review.
- Deferred docs follow-up: none for FH-025.

## Required Checks And Gate Output Evidence

- Required check: initial git status before edits
  Command: `git status --short`
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  (no output)
  ```
  Notes: Worktree was clean before edits; no stop condition triggered.

- Required check: project gate preflight
  Command: `.venv/bin/python scripts/project_gate.py preflight`
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  working_directory: /opt/jc-coach
  branch: agentdev
  git status --short -uall
  (no output)
  governance files
  AGENTS.md: present
  docs/CURRENT_STATUS.md: present
  docs/HANDOFF.md: present
  docs/project_management/WP_REGISTRY.md: present
  docs/project_management/AGENT_WORKFLOW.md: present
  docs/TESTING.md: present
  production DB SHA
  2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
  ```
  Notes: Read-only preflight evidence only.

- Required check: project gate changed
  Command: `.venv/bin/python scripts/project_gate.py changed`
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  ## changed/untracked files
   M docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md
   M docs/project_management/AGENT_WORKFLOW.md
  ?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-025_add-gate-output-requirement-to-task-report-template_report.md

  ## activated guardians
  DOCUMENTATION_STEWARD
  PM_ORCHESTRATOR
  ```
  Notes: Changed files are limited to the two allowed documentation contract
  files plus the required FH-025 report path.

- Required check: project gate required-checks
  Command: `.venv/bin/python scripts/project_gate.py required-checks`
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  ## mandatory local gate expectations
  - .venv/bin/python scripts/project_gate.py preflight
  - .venv/bin/python scripts/project_gate.py changed
  - .venv/bin/python scripts/project_gate.py required-checks
  - .venv/bin/python scripts/project_gate.py postflight
  - git diff --check

  DOCUMENTATION_STEWARD:
  - REQUIRED: complete the report docs update checklist
  - REQUIRED: confirm Hot/current status docs updated or not required
  - REQUIRED: confirm navigation docs updated or not required
  - RECOMMENDED: check changed docs do not weaken AGENTS.md or control-plane policy
  PM_ORCHESTRATOR:
  - REQUIRED: confirm no unauthorized git add/commit/push
  ```
  Notes: The additional safe docs-only checks were performed in this report:
  docs update checklist, Hot/status no-update rationale, navigation no-update
  rationale, control-plane scope review and unauthorized git action review.

- Required check: project gate postflight
  Command: `.venv/bin/python scripts/project_gate.py postflight`
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  ## git diff --stat
  .../07_CODEX_EXECUTION_HANDOFF.md                  | 23 ++++++++++++--
  docs/project_management/AGENT_WORKFLOW.md          | 35 ++++++++++++++--------
  2 files changed, 43 insertions(+), 15 deletions(-)

  ## changed/untracked files
   M docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md
   M docs/project_management/AGENT_WORKFLOW.md
  ?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-025_add-gate-output-requirement-to-task-report-template_report.md

  ## required-check summary
  code/test/script change: no
  activated guardians: DOCUMENTATION_STEWARD, PM_ORCHESTRATOR

  ## production DB SHA
  2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
  ```
  Notes: Postflight reflects the final intended file set. The report file is
  untracked because Executor was not authorized to run `git add`.

- Required check: whitespace diff check
  Command: `git diff --check`
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  (no output)
  ```
  Notes: No whitespace errors reported.

- Required check: scope and allowed-file review
  Command: Manual review against Task Card allowed files and forbidden actions.
  Status: PASS
  Output excerpt or artifact/log path:
  ```text
  Changed/created files are limited to:
  docs/project_management/AGENT_WORKFLOW.md
  docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md
  docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-025_add-gate-output-requirement-to-task-report-template_report.md
  ```
  Notes: No product behavior, scripts, tests, CI provider configuration, status
  docs, DB/data, runtime/service/deploy config or package files were changed.

## Checks Not Run And Why

- `.venv/bin/python scripts/local_quality_gate.py`: not run; task-authorized
  skip. FH-025 is docs/governance-only and the Task Card explicitly says not to
  run the local quality gate.
- Full pytest: not run; task-authorized skip. Scripts/tests/CI config are
  forbidden in this task, and docs-only governance tasks do not require pytest
  unless the Task Card or changed files require it.
- Ruff: not run; task-authorized skip. No code/script/test files changed and
  the Task Card explicitly limits checks to docs-safe gates and `git diff
  --check`.
- Live app/runtime smoke: not run; task-authorized skip. Runtime/service work
  is forbidden.
- Service start/stop/restart, nginx/systemd/deploy checks: not run;
  task-authorized skip. Service/deploy mutation is forbidden.
- Steam/Valve import, parser, evaluator and manual evaluator commands: not run;
  task-authorized skip. These actions are forbidden for FH-025.
- Package installation/network/hosted CI setup: not run; task-authorized skip.
  These actions are forbidden for FH-025.

## Failed/Stalled/Timed-Out Checks

None for FH-025.

Known residual external/pre-existing issue preserved: the full safe pytest
suite has a known stall in
`tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`
when run as part of the full suite. FH-025 does not fix, risk-accept for final
readiness or mark that stall irrelevant.

## DB/Import/Runtime/Service Safety

- Production DB mutation: no.
- Schema mutation: no.
- DB files or generated data edited: no.
- Live Steam/Valve import: no.
- Parser jobs: no.
- Evaluator/manual evaluator jobs: no.
- Runtime app, service, nginx, systemd or deploy config changes: no.
- Package installation: no.
- Hosted CI/provider setup, `.github` files, secrets or branch protection: no.
- `git add`, commit or push: no.

## Production DB SHA

Read-only SHA reported by project gate preflight/postflight:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

The production DB was not mutated.

## Residual Risks

- The known full-suite pytest stall remains open and visible as a residual
  quality-gate risk. Owner/target follow-up remains a future hardening task
  selected by PM/user; FH-025 does not broaden into fixing or accepting it.
- Hosted CI/provider setup remains out of scope and a future explicit user
  decision/task.
- Final readiness gate remains not passed; `READY_FOR_MAJOR_CS2_FEATURE_WORK`
  remains `NO`.

## Next Recommended Task

No Executor-selected task. PM/user should continue with the next approved
foundation hardening task card. FH-025 introduces no required follow-up of its
own.

## Stop Conditions Encountered

None.
