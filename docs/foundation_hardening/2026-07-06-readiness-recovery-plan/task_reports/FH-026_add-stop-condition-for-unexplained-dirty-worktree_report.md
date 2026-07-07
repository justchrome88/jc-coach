# FH-026 Add Stop Condition For Unexplained Dirty Worktree Report

Date: 2026-07-07

Task: `FH-026 Add stop condition for unexplained dirty worktree`

Result: `PASS`

## Summary

Updated `docs/project_management/AGENT_WORKFLOW.md` to make unexplained
dirty or untracked main-repo state a stop condition before WP-level or
hardening Executor work starts.

The rule now distinguishes pre-existing unexplained worktree state from normal
scoped task edits made after a clean or accepted preflight, and it names the
required `BLOCKED` report evidence.

## Files Changed

- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-026_add-stop-condition-for-unexplained-dirty-worktree_report.md`

## Evidence

### Initial Worktree State

Command:

```bash
git status --short
```

Result: `PASS`

Output:

```text
(no output)
```

The main repo was clean before edits. The unexplained-dirty-worktree stop
condition did not trigger for this task.

### Project Gate Preflight

Command:

```bash
.venv/bin/python scripts/project_gate.py preflight
```

Result: `PASS`

Relevant output:

```text
## task context
working_directory: /opt/jc-coach
branch: agentdev

## git status --short -uall
(no output)

## governance files
AGENTS.md: present
docs/CURRENT_STATUS.md: present
docs/HANDOFF.md: present
docs/project_management/WP_REGISTRY.md: present
docs/project_management/AGENT_WORKFLOW.md: present
docs/TESTING.md: present

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

### Project Gate Changed

Command:

```bash
.venv/bin/python scripts/project_gate.py changed
```

Result: `PASS`

Output:

```text
## changed/untracked files
 M docs/project_management/AGENT_WORKFLOW.md

## activated guardians
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR
```

### Project Gate Required Checks

Command:

```bash
.venv/bin/python scripts/project_gate.py required-checks
```

Result: `PASS`

Relevant output:

```text
## mandatory local gate expectations
- .venv/bin/python scripts/project_gate.py preflight
- .venv/bin/python scripts/project_gate.py changed
- .venv/bin/python scripts/project_gate.py required-checks
- .venv/bin/python scripts/project_gate.py postflight
- git diff --check

## required checks by activated guardian
DOCUMENTATION_STEWARD:
- REQUIRED: complete the report docs update checklist
- REQUIRED: confirm Hot/current status docs updated or not required
- REQUIRED: confirm navigation docs updated or not required
- RECOMMENDED: check changed docs do not weaken AGENTS.md or control-plane policy
PM_ORCHESTRATOR:
- REQUIRED: .venv/bin/python scripts/project_gate.py preflight
- REQUIRED: .venv/bin/python scripts/project_gate.py changed
- REQUIRED: .venv/bin/python scripts/project_gate.py required-checks
- REQUIRED: .venv/bin/python scripts/project_gate.py postflight
- REQUIRED: git diff --check
- REQUIRED: confirm no unauthorized git add/commit/push
- RECOMMENDED: include initial git status, changed files, guardians and final git status in report
```

### Diff Review

Command:

```bash
git diff -- docs/project_management/AGENT_WORKFLOW.md
```

Result: `PASS`

Relevant findings:

- Lifecycle step 4 now requires a clean worktree or explained dirty/untracked
  state before WP-level or hardening Executor work starts.
- The WP-level invocation mode stop condition now names unexplained
  dirty/untracked pre-start state.
- Standard WP preflight now requires a `BLOCKED` report with `git status
  --short`, safe preflight evidence, affected paths, why the state is
  unexplained, and the minimum next action.
- The rule now says normal scoped edits after clean/accepted preflight are
  reported through changed-files, postflight and `git diff --check` evidence
  instead of treated as a blocker.

### Project Gate Postflight

Command:

```bash
.venv/bin/python scripts/project_gate.py postflight
```

Result: `PASS`

Relevant output:

```text
## git diff --stat
docs/project_management/AGENT_WORKFLOW.md | 31 +++++++++++++++++++++++++++----
 1 file changed, 27 insertions(+), 4 deletions(-)

## changed/untracked files
 M docs/project_management/AGENT_WORKFLOW.md
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-026_add-stop-condition-for-unexplained-dirty-worktree_report.md

## activated guardians
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR

## required-check summary
code/test/script change: no
activated guardians: DOCUMENTATION_STEWARD, PM_ORCHESTRATOR

## governance files
AGENTS.md: present
docs/CURRENT_STATUS.md: present
docs/HANDOFF.md: present
docs/project_management/WP_REGISTRY.md: present
docs/project_management/AGENT_WORKFLOW.md: present
docs/TESTING.md: present

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

### Whitespace Check

Command:

```bash
git diff --check
```

Result: `PASS`

Output:

```text
(no output)
```

## Required Checks Summary

- `git status --short` before edits: `PASS`
- `.venv/bin/python scripts/project_gate.py preflight`: `PASS`
- `.venv/bin/python scripts/project_gate.py changed`: `PASS`
- `.venv/bin/python scripts/project_gate.py required-checks`: `PASS`
- `.venv/bin/python scripts/project_gate.py postflight`: `PASS`
- `git diff --check`: `PASS`
- Allowed-file and control-plane scope review: `PASS`

No required checks were skipped, failed, stalled or timed out.

## Docs Update Checklist

- Hot/current status docs: `checked; no update required` - this task changed a
  workflow rule but did not change product version, active WP state, promotion
  status or current blockers.
- WP registry/status/handoff docs: `checked; no update required` - no WP ID,
  dependency, promotion status or handoff bootstrap state changed.
- Navigation docs: `checked; no update required` - no new canonical or
  navigation document was created; an existing workflow doc was updated in
  place.
- Task-relevant domain docs: `checked and updated` -
  `docs/project_management/AGENT_WORKFLOW.md` now contains the stop condition
  and report evidence requirement.
- Documentation Steward: `checked and completed` - scoped review confirmed the
  task was an explicit governance/control-plane docs change, no duplicate doc
  was created and no archive/delete/move action was performed.
- Deferred docs follow-up: `none`.

## Safety Declarations

- Docs-only task: yes.
- Product code changed: no.
- Scripts/tests changed: no.
- DB/data mutated: no.
- Production DB SHA observed by preflight:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Live Steam/Valve import run: no.
- Parser/evaluator/manual evaluator jobs run: no.
- Service/deploy/nginx/systemd changes: no.
- Package installation: no.
- Persistent app reports generated: no.
- Forbidden files touched: no.
- `git add` run: no.
- Commit run: no.
- Push run: no.
- Secret values observed: no.
- External documentation lookup: not used; this was a docs-only internal
  governance task.

## Context Discipline

- Context manifest used: yes.
- Broad reads avoided: yes; forbidden-by-default audit/task/instruction trees
  were not read.
- Additional allowed Warm docs read: `docs/project_management/AGENT_WORKFLOW.md`
  and `docs/agents/roles/DOCUMENTATION_STEWARD.md`.
- PM-side hot file read from manifest: `/opt/jc-coach-pm/AGENTS.md`.
- PM memory files were not read because the Task Card, manifest and main-repo
  Hot/Warm context were sufficient and there was no detected conflict.

## Token Metrics

- PM_CREATE tokens: `UNKNOWN`.
- EXECUTOR tokens: `UNKNOWN`.
- PM_REVIEW tokens: `UNKNOWN`.
- Total cycle tokens: `UNKNOWN`.
- Task verdict: `PASS`.
- Quality verdict: `PENDING_PM_REVIEW`.
- Number of broad reads avoided: `at least 4 forbidden-by-default groups`.
- Context manifest was used: `true`.

## Blockers

None.

## Next WP

PM review of FH-026. Do not claim final readiness or
`READY_FOR_MAJOR_CS2_FEATURE_WORK`.
