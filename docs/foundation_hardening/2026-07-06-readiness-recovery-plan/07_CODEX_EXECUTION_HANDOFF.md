# Codex Execution Handoff

Date: 2026-07-07.

## Context

JC Coach / CS2 AI Coach completed a read-only agentic-readiness audit.

Audit folder:

```text
docs/audits/2026-07-06-agentic-readiness-audit
```

Foundation hardening plan folder:

```text
docs/foundation_hardening/2026-07-06-readiness-recovery-plan
```

Current status:

```text
CONTINUE WITH RESTRICTED SCOPE
READY_FOR_MAJOR_CS2_FEATURE_WORK: NO
```

Audit score: 66% / 3.30 of 5 across 106 audit rows. Evidence:
`00_EXECUTIVE_SUMMARY.md`.

## First Tasks In Order

1. Create or update canonical risk register / enriched known limitations.
2. Add mandatory local quality gate or CI-equivalent gate workflow.
3. Create migration baseline and schema gate.
4. Define source trust and sample-size policy.
5. Add prompt/payload versioning plan or implementation if schema-safe.
6. Build first semantic AI eval suite.
7. Design diagnosis registry and recommendation planner.
8. Expand architecture map and API contracts.
9. Add CS2 domain pack document.
10. Plan durable import worker and retry ledger.

This order follows audit `10_NEXT_10_TASKS.md`, with risk/gate work pulled
early so later execution has stronger controls.

## Strict Rules

- No unrelated changes.
- No production DB mutation.
- No live Steam/Valve import.
- No parser jobs on production data.
- No evaluator or manual evaluator on production DB.
- No major CS2 feature work.
- No broad refactor without explicit approval.
- No import cap raise.
- No service/nginx/systemd/deploy mutation.
- No package installation unless explicitly approved.
- No secret values in output.
- Every task must include diff summary.
- Every task must identify required checks before work starts.
- Every task must include required checks, checks actually run, checks not run
  with exact reasons, failed/stalled/timed-out checks and residual risk/owner/
  target follow-up when relevant.
- Every WP-level, hardening or file-backed Executor report must include gate
  output evidence for each required check: command, result status and a relevant
  output excerpt or artifact/log path. Long command output may be summarized,
  but a bare "passed" statement is not enough for PM review.
- If a required check is not run, the report must state the exact reason and
  whether the skip was explicitly task-authorized. If a required check fails,
  stalls or times out, the report must state the exact failure/stall/timeout
  summary, residual risk, owner and target follow-up when relevant.
- Every task must include the docs update checklist from
  `docs/project_management/AGENT_WORKFLOW.md`, not only a free-form docs
  summary.
- Every task must include residual risks.
- For code, script or test changes, `.venv/bin/python
  scripts/local_quality_gate.py` is the accepted local CI-equivalent PASS gate
  for the restricted foundation-hardening lane.
- For code, script or test changes, that local gate covers project gate
  preflight, changed, required-checks and postflight evidence; full safe
  pytest; Ruff; and `git diff --check`, unless the Task Card asks for separate
  subcommand output.
- Docs-only governance/status/report tasks are not required to run pytest, Ruff
  or the local quality gate unless the Task Card or changed files require them.
  Their PASS requirements remain docs-safe project gate commands,
  `git diff --check`, scope/allowed-file review and task-specific checks.
- `PASS` is forbidden when a required task/change-class check is missing,
  failed, stalled, timed out or skipped without explicit task authorization.
- `PASS_WITH_WARNINGS` must not be used to imply that a mandatory gate passed
  when it did not; use `FAIL` for completed work with failed required checks
  and `BLOCKED` for stop conditions or checks that cannot safely run.
- Docs-only tasks must not run live app, service, import, parser, evaluator or
  manual evaluator commands unless a Task Card explicitly authorizes them.

## Accepted Local CI-Equivalent Gate

The accepted repo-local CI-equivalent gate is:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

Use this gate before claiming PASS for code, script or test changes, subject to
stricter Task Card requirements. It is accepted as the local CI-equivalent path
until a future explicit task chooses and configures hosted CI or another
external provider.

This is not hosted CI and does not authorize `.github` workflow files, external
accounts, secrets, package installation, branch protection or provider setup.
Hosted CI remains a separate future user decision and configuration task.

This local gate also does not prove final readiness by itself. The known
full-suite pytest stall in
`tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`
remains an unresolved residual quality-gate risk, not a resolved condition and
not final-readiness evidence.

## Definition Of Done For Each Hardening Task

A task is done only when:

- scope matches the Task Card;
- changed files are listed;
- no unrelated files are changed;
- required docs are updated or explicitly not needed;
- the report's docs update checklist covers Hot/current status docs,
  WP registry/status/handoff docs, navigation docs, task-relevant domain docs,
  Documentation Steward applicability and deferred docs follow-up;
- required tests/checks are run and reported;
- missing, skipped, failed, stalled or timed-out checks are reported with exact
  reasons and residual risk;
- every required check has reviewable gate output evidence: command, status and
  output excerpt or artifact/log path, with exact not-run/failure/stall/timeout
  detail when applicable;
- DB/import/runtime/service safety is declared;
- production DB SHA is reported for DB-impacting or DB-risk tasks;
- residual risks and follow-up tasks are listed;
- `git diff --check` passes.
- the final verdict follows the mandatory PASS policy: required checks passed
  for `PASS`, passed with non-blocking risks for `PASS_WITH_WARNINGS`, failed
  required checks for `FAIL` or unsafe/unavailable required checks for
  `BLOCKED`.

## Standard Task Handoff Format

Use this report shape after each task:

```text
Result:
Verdict: PASS / PASS_WITH_WARNINGS / FAIL / BLOCKED

Scope:

Files changed:

Diff summary:

Gate output requirement summary:

Mandatory PASS policy summary:

Docs update checklist:
- Hot/current status docs:
- WP registry/status/handoff docs:
- Navigation docs:
- Task-relevant domain docs:
- Documentation Steward:
- Deferred docs follow-up:

Required checks and gate output evidence:
- Required check:
  Command:
  Status:
  Output excerpt or artifact/log path:
  Notes:

Checks not run and why:

Failed/stalled/timed-out checks:

DB/import/runtime/service safety:

Production DB SHA:

Residual risks:

Next recommended task:

Stop conditions encountered:
```

## Stop Conditions

Stop and report `BLOCKED` if:

- production DB mutation would be required without authorization;
- schema implementation is requested before migration baseline is accepted;
- public/friends access work appears in scope;
- task requires import/parser/evaluator/service/deploy action without explicit
  authorization;
- audit evidence conflicts with current Hot context;
- secret values appear in any output;
- main repo has unexplained unrelated changes before starting.
