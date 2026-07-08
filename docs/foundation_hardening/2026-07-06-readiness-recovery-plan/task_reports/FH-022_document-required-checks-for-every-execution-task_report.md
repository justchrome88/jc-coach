# FH-022 Document Required Checks For Every Execution Task - Report

Result:
Verdict: PASS_WITH_WARNINGS

Scope:
- Documented required-check expectations for future Executor task/change
  classes.
- Updated standard report/handoff expectations so reports must include required
  checks, checks run, checks not run with exact reasons, failed/stalled checks
  and residual risk/follow-up.
- Preserved `.venv/bin/python scripts/local_quality_gate.py` as the standard
  local PASS gate for code, script or test changes.
- Did not broaden into CI configuration, mandatory PASS enforcement,
  product/application behavior, DB/schema, import/parser/evaluator,
  runtime/service/deploy, AI/metrics implementation or final readiness work.

Files changed:
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/TESTING.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-022_document-required-checks-for-every-execution-task_report.md`

Diff summary:
- `AGENT_WORKFLOW.md`: added a required-checks preflight rule, a compact
  matrix for docs-only, code/script/test, DB/schema-risk,
  import/parser/evaluator-risk, runtime/deploy/service-risk, UI/web,
  recommendation/coach/metrics/AI and audit/review/discovery tasks; expanded
  output and closure checklist requirements.
- `docs/TESTING.md`: added the same task-class check expectations and the rule
  that skipped/failed checks require exact reporting and residual risk.
- `07_CODEX_EXECUTION_HANDOFF.md`: updated strict rules, done definition and
  standard report format to require required-checks evidence and skipped/
  failed/stalled check disclosure.

Required-checks policy summary:
- Task Cards may make generic check defaults stricter, add targeted checks or
  forbid otherwise safe checks.
- Future Executor reports must list required checks, checks actually run,
  checks not run with exact reasons, failed/stalled/timed-out checks and
  residual risk/owner/target follow-up where relevant.
- Docs-only work is not forced to run live app, service, import, parser,
  evaluator or manual evaluator commands.
- DB/schema, import/parser/evaluator and runtime/service actions still require
  explicit Task Card authorization and task-specific safety evidence before any
  risky action.
- Code, script or test changes retain `.venv/bin/python
  scripts/local_quality_gate.py` as the standard local PASS gate.

Docs update checklist:
- Hot/current status docs: checked; no update required. FH-022 is scoped to
  check-policy docs and does not change product status, active WP state or
  readiness status.
- WP registry/status/handoff docs: checked; `WP_REGISTRY.md`, `CURRENT_STATUS.md`
  and `HANDOFF.md` did not need edits and are outside the allowed file list.
  The task-scoped hardening execution handoff was updated.
- Navigation docs: checked; no update required. No new canonical/navigation doc
  was created.
- Task-relevant domain docs: checked and updated. `AGENT_WORKFLOW.md`,
  `docs/TESTING.md` and the hardening execution handoff now contain the
  required-checks policy.
- Documentation Steward: completed in-task because canonical/Warm governance
  and testing docs changed; updates stayed inside the Task Card allowed files.
- Deferred docs follow-up: none for FH-022. FH-023/FH-024 remain separate for
  CI/local equivalent policy and mandatory PASS enforcement.

Tests/checks run:
- `git status --short` before edits: clean output.
- `.venv/bin/python scripts/project_gate.py changed`: PASS. Changed/untracked
  files were limited to the three allowed docs plus this required FH-022 report;
  activated guardians were `DOCUMENTATION_STEWARD` and `PM_ORCHESTRATOR`.
- `.venv/bin/python scripts/project_gate.py required-checks`: PASS. It required
  project gate preflight/changed/required-checks/postflight, `git diff --check`,
  docs update checklist completion, Hot/current status and navigation doc
  confirmation, no unauthorized git add/commit/push confirmation and a check
  that the changed docs do not weaken `AGENTS.md` or control-plane policy.
- `.venv/bin/python scripts/project_gate.py preflight`: PASS. Run because
  `project_gate.py required-checks` listed it as required.
- `.venv/bin/python scripts/project_gate.py postflight`: PASS. It reported no
  code/test/script change, activated guardians `DOCUMENTATION_STEWARD` and
  `PM_ORCHESTRATOR`, governance files present and production DB SHA
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- `git diff --check`: PASS.
- `sha256sum data/cs2_coach.db`: PASS/read-only evidence, SHA
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Final `git status --short`: expected scoped docs/report changes only.

Checks not run and why:
- `.venv/bin/python scripts/local_quality_gate.py`: not required for this
  docs/governance-only task; scripts/tests/code changes were forbidden.
- Full pytest/Ruff: not required by the Task Card for FH-022 and full-suite
  pytest has a known pre-existing FH-021 residual stall in
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
- Live app/service/import/parser/evaluator/manual evaluator commands: forbidden
  by the Task Card for this docs/governance-only task.

Failed/stalled/timed-out checks:
- None in FH-022 checks.

DB/import/runtime/service safety:
- No production DB mutation.
- No schema changes.
- No live Steam/Valve import.
- No parser jobs.
- No evaluator or manual evaluator jobs.
- No service start/stop/restart or deploy/nginx/systemd changes.
- No package installation.
- No `git add`, commit or push.

Production DB SHA:
- `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`
  (`sha256sum data/cs2_coach.db`, read-only).

Residual risks:
- Pre-existing FH-021 residual risk remains: the full pytest suite still stalls
  in `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
  FH-022 does not claim final readiness, a green full-suite state or risk
  acceptance for that stall.
- This task documents the required-checks policy only. It does not implement CI
  configuration or mandatory PASS enforcement; FH-023/FH-024 remain the
  appropriate follow-up scope.

Next recommended task:
- FH-023 for CI configuration or accepted local CI-equivalent policy, or the
  next PM-selected foundation-hardening task. Do not treat FH-022 as final
  readiness gate work.

Stop conditions encountered:
- None.
