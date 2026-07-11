# FH-024 Make Pytest/Ruff/Git Diff/Project Gate Mandatory For PASS Report

Result:
Verdict: PASS

Scope:
Scoped documentation/governance execution for FH-024. Updated only allowed
workflow, testing and foundation-hardening docs so future Executor PASS verdicts
are blocked when required checks are missing, failed, stalled, timed out or
skipped without explicit task authorization.

Files changed:
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/TESTING.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/05_EXECUTION_PLAN.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-024_make-pytest-ruff-git-diff-project-gate-mandatory-for-pass_report.md`

Diff summary:
- Added explicit PASS verdict policy to `AGENT_WORKFLOW.md`.
- Clarified that code, script and test changes require the accepted local
  CI-equivalent gate before PASS.
- Clarified that the local gate covers project gate preflight, changed,
  required-checks and postflight evidence; full safe pytest; Ruff; and
  `git diff --check`.
- Clarified docs-only governance/status/report task checks and preserved the
  practical no-pytest/no-Ruff/no-local-gate default unless a Task Card or
  changed files require them.
- Replaced stale FH-024 future-scope wording in the execution handoff and agent
  workflow with current mandatory PASS policy.
- Preserved hosted CI/provider setup as future explicit user-decision work.
- Preserved the known full-suite pytest stall as an unresolved residual
  quality-gate risk.

Mandatory PASS policy summary:
- `PASS` is allowed only when every required check for the task/change class and
  Task Card passes, or when a Task Card explicitly authorizes a narrower check
  set and the report names that authorization.
- `PASS` is forbidden when a required check is missing, failed, stalled, timed
  out or skipped without explicit task authorization.
- `PASS_WITH_WARNINGS` is allowed only when required checks passed but
  non-blocking warnings or residual risks remain.
- `FAIL` is for completed scoped work with failed required acceptance checks.
- `BLOCKED` is for stop conditions, missing authorization or required checks
  that cannot safely run.

Docs update checklist:
- Hot/current status docs: checked; no update required. Task Card forbade edits
  to `docs/CURRENT_STATUS.md`, `docs/project_management/WP_REGISTRY.md` and
  `docs/HANDOFF.md`; no conflict was found with current restricted-scope state.
- WP registry/status/handoff docs: checked; no update required. FH-024 does not
  change product status, roadmap state or WP registry state.
- Navigation docs: checked; no update required. No new canonical/navigation doc
  was created; this report lives in the existing hardening task report folder.
- Task-relevant domain docs: checked and updated. Updated the allowed workflow,
  testing and foundation-hardening quality-gate docs.
- Documentation Steward: checked and completed in scoped form through this
  docs update checklist and allowed-file review.
- Deferred docs follow-up: none for FH-024. Hosted CI/provider setup and the
  known full-suite pytest stall remain separate future tasks.

Tests/checks run:
- `git status --short` before edits: passed; no output, clean worktree.
- `.venv/bin/python scripts/project_gate.py preflight`: passed.
- `.venv/bin/python scripts/project_gate.py changed`: passed.
  Activated guardians: `DOCUMENTATION_STEWARD`, `PM_ORCHESTRATOR`.
- `.venv/bin/python scripts/project_gate.py required-checks`: passed.
  Required documentation-steward confirmations were completed in this report.
- `.venv/bin/python scripts/project_gate.py postflight`: passed.
  Postflight reported no code/test/script change and the same production DB SHA.
- `git diff --check`: passed.
- Scope/allowed-file review: passed; only allowed files changed.
- Control-plane review: passed; changes strengthen the allowed governance docs
  for FH-024 and do not weaken `AGENTS.md`, DB safety, import/parser/evaluator
  safety, service/deploy safety, control-plane protection or public/friends
  restrictions.
- Final `git status --short`: expected scoped docs/report changes only:
  five modified allowed docs and one untracked allowed FH-024 report file.

Checks not run and why:
- `.venv/bin/python scripts/local_quality_gate.py`: not run; task card
  explicitly forbids it for this docs/governance-only task.
- Full pytest: not run; task card explicitly forbids it for this
  docs/governance-only task.
- Ruff: not run; task card explicitly forbids it for this docs/governance-only
  task.
- Live app/service/import/parser/evaluator/manual evaluator commands: not run;
  forbidden by task card and not needed for docs-only policy work.

Failed/stalled/timed-out checks:
- None during FH-024.
- Known pre-existing residual risk remains: full-suite pytest can stall in
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
  FH-024 did not fix or risk-accept that stall.

DB/import/runtime/service safety:
- No production DB mutation.
- No schema changes.
- No DB/data files edited.
- No live Steam/Valve import.
- No parser jobs.
- No evaluator or manual evaluator jobs.
- No app, service, nginx, systemd or deploy changes.
- No package installation.
- No hosted CI/provider, `.github`, branch protection, secrets or network setup.
- No `git add`, commit or push.

Production DB SHA:
- Preflight reported:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db`
- No DB mutation was authorized or performed.

Residual risks:
- Hosted CI/provider setup remains a separate future user decision/task.
- Known full-suite pytest stall remains unresolved and must remain visible in
  future gate/readiness reporting.
- FH-024 is policy documentation enforcement only; it does not add automated
  CI/provider enforcement or repair test-suite behavior.

Next recommended task:
- Continue the foundation-hardening sequence with the next explicit Task Card.
  Likely candidates remain outside FH-024 scope: resolve the known full-suite
  pytest stall or continue the next approved P0/P1 hardening item.

Stop conditions encountered:
- None.
