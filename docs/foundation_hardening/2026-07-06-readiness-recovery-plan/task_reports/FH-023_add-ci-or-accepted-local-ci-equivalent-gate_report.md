# FH-023 Add CI Or Accepted Local CI-Equivalent Gate Report

Date: 2026-07-07.

## Result

Verdict: PASS_WITH_WARNINGS

FH-023 established `.venv/bin/python scripts/local_quality_gate.py` as the
accepted repo-local CI-equivalent gate for JC Coach during the restricted
foundation-hardening lane, until a future explicit task chooses and configures
hosted CI or another external provider.

## Scope

Scoped documentation/governance execution only. This task updated allowed
testing/workflow/handoff documentation and created this report.

No product application behavior, scripts, tests, CI provider config, DB/schema,
runtime/service/deploy, import/parser/evaluator, package installation, hosted
CI setup, branch protection, secrets or final readiness gate work was performed.

## Files Changed

- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/TESTING.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-023_add-ci-or-accepted-local-ci-equivalent-gate_report.md`

## Diff Summary

- Named `.venv/bin/python scripts/local_quality_gate.py` as the accepted local
  CI-equivalent gate for code, script and test changes during restricted
  foundation hardening.
- Clarified that the local CI-equivalent gate is not hosted CI and does not add
  `.github` workflows, external accounts, secrets, package installs, branch
  protection or provider setup.
- Preserved hosted CI as a separate future user policy/configuration decision.
- Preserved FH-024 mandatory PASS enforcement as separate future scope.
- Recorded the known full-suite pytest stall as an unresolved residual
  quality-gate risk, not a resolved condition or final-readiness acceptance.

## Local CI-Equivalent Gate Summary

Accepted local CI-equivalent gate:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

For code, script or test changes, Executor reports must use this command as the
standard local CI-equivalent PASS gate, subject to stricter Task Card
requirements. If it fails, stalls or times out, the report must name the exact
command and verdict impact.

## Hosted CI Non-Scope / Future Decision

Hosted CI was not configured. This task did not create or edit `.github` files,
external CI provider configuration, external accounts, secrets, package
installation steps or branch protection.

Hosted CI remains a separate future decision and configuration task if the user
chooses that path.

## Docs Update Checklist

- Hot/current status docs: checked; no update required. Task Card explicitly
  forbade edits to `docs/CURRENT_STATUS.md`, and this task did not change
  current project status or readiness flags.
- WP registry/status/handoff docs: checked and updated where allowed. The
  task-relevant hardening execution handoff was updated; `WP_REGISTRY.md` and
  `docs/HANDOFF.md` were explicitly forbidden and did not need changes for this
  bounded policy clarification.
- Navigation docs: checked; no update required. No new canonical navigation doc
  was created and existing doc locations did not change.
- Task-relevant domain docs: checked and updated. `docs/TESTING.md`,
  `docs/project_management/AGENT_WORKFLOW.md` and the hardening execution
  handoff now record the accepted local CI-equivalent policy.
- Documentation Steward: completed as part of this governance/docs task by
  checking Hot/Warm scope, allowed files, source-of-truth restrictions and
  deferred follow-up.
- Deferred docs follow-up: none for FH-023. Future hosted CI setup and FH-024
  mandatory PASS enforcement remain separate tasks.

## Tests/Checks Run

- `git status --short` before edits: clean output.
- `.venv/bin/python scripts/project_gate.py preflight`: PASS. Run because
  `project_gate.py required-checks` listed it as required PM/Orchestrator
  evidence. It reported branch `agentdev`, the scoped changed/untracked files,
  governance files present and production DB SHA read-only evidence.
- `.venv/bin/python scripts/project_gate.py changed`: PASS. Reported only the
  three scoped docs files modified plus this untracked FH-023 report; activated
  guardians were `DOCUMENTATION_STEWARD` and `PM_ORCHESTRATOR`.
- `.venv/bin/python scripts/project_gate.py required-checks`: PASS. Reported
  docs/governance checks, docs update checklist, Hot/status and navigation
  confirmations, no unauthorized git action confirmation and `git diff --check`.
- `.venv/bin/python scripts/project_gate.py postflight`: PASS. Reported docs
  diff stat, scoped changed/untracked files, active guardians and production DB
  SHA read-only evidence.
- `git diff --check`: PASS.
- Final `git status --short`: scoped modified docs plus untracked FH-023 report
  only.

## Checks Not Run And Why

- `.venv/bin/python scripts/local_quality_gate.py`: not run because FH-023 is
  docs/governance-only and the Task Card explicitly forbids running it for this
  task.
- Full pytest: not run because FH-023 is docs/governance-only and the Task Card
  forbids it. Known residual risk remains the full-suite stall in
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
- Ruff: not run because scripts/tests/code were forbidden and the Task Card
  required only project gate docs evidence plus `git diff --check`.
- Live app, service, import, parser, evaluator and manual evaluator commands:
  not run; forbidden by scope.

## Failed/Stalled/Timed-Out Checks

None during FH-023.

Known pre-existing residual risk remains: full-suite pytest stalls in
`tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.

## DB/Import/Runtime/Service Safety

- Production DB mutation: none.
- Schema changes: none.
- DB files or generated data edited: none.
- Live Steam/Valve import: not run.
- Parser jobs: not run.
- Evaluator/manual evaluator jobs: not run.
- Service/nginx/systemd/deploy actions: not run.
- Package installation/network-dependent setup: not run.
- `git add`, commit and push: not run.

## Production DB SHA

Read-only project gate evidence reported:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

No DB-impacting commands were run and production DB mutation was forbidden.

## Residual Risks

- Full-suite pytest stall remains unresolved and is not accepted as final
  readiness evidence.
- Hosted CI is not present; the accepted gate is local CI-equivalent only.
- FH-024 mandatory PASS enforcement remains future scope.
- Final readiness gate remains `FAIL` until the full hardening gate criteria
  are satisfied by a separate final review.

## Next Recommended Task

FH-024 mandatory PASS enforcement, or another explicitly approved hardening
task selected by PM/User.

## Stop Conditions Encountered

None.
