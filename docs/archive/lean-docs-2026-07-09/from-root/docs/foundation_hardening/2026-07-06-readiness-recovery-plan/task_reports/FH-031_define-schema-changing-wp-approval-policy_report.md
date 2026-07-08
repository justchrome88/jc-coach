# FH-031 Define Schema-Changing WP Approval Policy Report

Date: 2026-07-07

Task: `FH-031 Define schema-changing WP approval policy`

Executor verdict: `BLOCKED`

PM resolution after manual gate rerun: `PASS_WITH_WARNINGS`

## Result

The scoped control-plane documentation edits were made. The original Executor
run correctly reported `BLOCKED` because the Task Card required
`.venv/bin/python scripts/local_quality_gate.py` and that required gate did not
complete in the Executor run. It stalled during full safe pytest after printing
progress dots and was interrupted, exiting `130`.

After that initial blocked result, the user manually reran the same required
local quality gate. The manual rerun completed successfully with
`LOCAL_QUALITY_GATE=PASS`, including full safe pytest, Ruff, `git diff --check`
and project gate postflight. PM review accepted FH-031 as `PASS_WITH_WARNINGS`
because the scoped docs diff was valid and the missing gate evidence was
repaired after the initial blocked run.

## Files Changed

- `AGENTS.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-031_define-schema-changing-wp-approval-policy_report.md`

## Summary Of Documentation Changes

- Added root-contract policy that schema-changing work is
  `approval-required` unless the Task Card explicitly names schema scope and
  allowed files.
- Defined schema work to include schema definition/code, startup schema
  behavior, migration or baseline artifacts, schema scripts, copied-DB
  experiments and production DB mutation.
- Added workflow-level schema Task Card requirements for scope category,
  allowed files/scripts/artifacts, production DB mutation authorization,
  backup/SHA evidence when mutation is authorized, FH-030 schema gate or
  successor evidence, and rollback/compatibility expectations.
- Added a small operating-protocol routing note pointing schema-changing WPs to
  the workflow policy.

## Checks And Evidence

### Initial Worktree Status

Command:

```bash
git status --short
```

Result: `PASS`

Output:

```text
(no output)
```

### Pre-Edit Project Gate Preflight

Command:

```bash
.venv/bin/python scripts/project_gate.py preflight
```

Result: `PASS`

Relevant output:

```text
working_directory: /opt/jc-coach
branch: agentdev

## git status --short -uall
(no output)

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

### Required Local Quality Gate

Command:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

Result: `BLOCKED` / did not complete; interrupted after prolonged no-progress
pytest output.

Exit status after interrupt: `130`

Relevant output before stall:

```text
LOCAL_QUALITY_GATE_ROOT=/opt/jc-coach

## project gate preflight
RESULT: PASS

## project gate changed
RESULT: PASS

## project gate required checks
RESULT: PASS

## full safe pytest
$ APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider
.....................................
```

No local-gate postflight, Ruff, or local-gate `git diff --check` evidence was
produced because the gate did not complete.

### Manual gate rerun evidence after initial BLOCKED result

Manual rerun log:

```text
/tmp/fh031_local_quality_gate_rerun.log
```

Command rerun:

```bash
.venv/bin/python scripts/local_quality_gate.py
```

Result: `PASS`

Relevant output:

```text
## full safe pytest
222 passed, 1 warning in 8.63s
RESULT: PASS

## ruff
All checks passed!
RESULT: PASS

## git diff check
RESULT: PASS

## project gate postflight
RESULT: PASS

LOCAL_QUALITY_GATE=PASS
```

The postflight evidence preserved the production DB SHA:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

### Git Diff Whitespace Check

Command:

```bash
git diff --check
```

Result: `PASS`

Output:

```text
(no output)
```

Final rerun after writing this report: `PASS`, `(no output)`.

### Postflight Project Gate

Command:

```bash
.venv/bin/python scripts/project_gate.py postflight
```

Result: `PASS`

Relevant output:

```text
## git diff --stat
AGENTS.md                                          | 11 ++++++-
 docs/project_management/AGENT_WORKFLOW.md          | 36 ++++++++++++++++++++++
 .../PROJECT_OPERATING_PROTOCOL.md                  |  7 ++++-
 3 files changed, 52 insertions(+), 2 deletions(-)

## changed/untracked files
 M AGENTS.md
 M docs/project_management/AGENT_WORKFLOW.md
 M docs/project_management/PROJECT_OPERATING_PROTOCOL.md

## activated guardians
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

### Final Worktree Status

Command:

```bash
git status --short
```

Result: `PASS`

Output:

```text
 M AGENTS.md
 M docs/project_management/AGENT_WORKFLOW.md
 M docs/project_management/PROJECT_OPERATING_PROTOCOL.md
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-031_define-schema-changing-wp-approval-policy_report.md
```

## Non-Changes

- No product logic changed.
- No application code changed.
- No tests changed.
- No DB files changed.
- No migration files or schema behavior changed.
- No migrations ran.
- Migration execution: `NO`
- No production DB mutation occurred.
- Production DB touched: `NO`
- No import, parser, evaluator or manual evaluator jobs ran.
- Live jobs run: `NO`
- No service, systemd, nginx or deploy changes occurred.
- Service restart: `NO`
- No package install occurred.
- Package install: `NO`
- No `git add`, commit or push occurred.
- No final readiness, hosted CI, green full-suite pytest or
  `READY_FOR_MAJOR_CS2_FEATURE_WORK` claim was made.

## DB Safety Declaration

Production DB path: `data/cs2_coach.db`

Production DB mutation: `NO`

Production DB SHA evidence from preflight/postflight:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

No backup was required because production DB mutation was not authorized and
did not occur.

## Documentation Steward Closure

Scope checked:

- Hot/canonical root contract: `AGENTS.md`
- Warm workflow/control policy:
  `docs/project_management/AGENT_WORKFLOW.md`
- Warm lifecycle/routing policy:
  `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`
- Task report

Classifications:

- `AGENTS.md`: `CANONICAL`
- `docs/project_management/AGENT_WORKFLOW.md`: `CANONICAL`
- `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`: `CANONICAL`
- This report: task evidence

Docs currency result: `PASS_FOR_SCOPED_DOC_CONTENT`

Closure result: `BLOCKED_BY_REQUIRED_CHECK`

Findings:

- The touched control-plane docs were explicitly authorized by this
  governance/control-plane Task Card.
- The new policy strengthens, rather than weakens, existing production DB and
  schema safety rules.
- No duplicate standalone policy document was created.
- No broad docs audit, archive, move or deletion was performed.

## Docs Update Checklist

- Hot/current status docs: `checked; no update required` because current
  project status, roadmap pause and active blockers did not change.
- WP registry/status/handoff docs: `checked; no update required` because this
  task is a foundation-hardening control-plane edit and did not create, close,
  defer or promote a registered WP.
- Navigation docs: `checked; no update required` because no new canonical doc,
  context level or navigation path was created.
- Task-relevant domain docs: `checked and updated` in `AGENTS.md`,
  `AGENT_WORKFLOW.md` and `PROJECT_OPERATING_PROTOCOL.md`.
- Documentation Steward: `checked and completed for scoped docs content`;
  overall closure remains blocked by the required local quality gate.
- Deferred docs follow-up: `none`.

## Residual Risks

- Required local quality gate evidence is incomplete because the gate stalled
  during pytest and was interrupted. This prevents a `PASS` verdict under the
  mandatory PASS policy.
- The known workflow-documented full-suite pytest stall risk remains unresolved
  and is not claimed fixed by this task.

## Blockers

- Required check `.venv/bin/python scripts/local_quality_gate.py` did not pass.

## Next Step

PM/User should decide whether to rerun FH-031 after resolving or explicitly
handling the local quality gate stall, or create a focused follow-up task for
the quality-gate stall before accepting this documentation patch.

## Forbidden Actions

Forbidden actions detected: `false`

Needs user decision: `true`
