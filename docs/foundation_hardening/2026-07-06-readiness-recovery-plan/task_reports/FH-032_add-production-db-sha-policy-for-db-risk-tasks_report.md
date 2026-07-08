# FH-032 Add Production DB SHA Policy For DB-Risk Tasks Report

Date: 2026-07-07

## Result

`PASS_WITH_WARNINGS`

FH-032 completed the scoped governance/control-plane documentation change. Root
`AGENTS.md` and `docs/project_management/AGENT_WORKFLOW.md` now distinguish:

- ordinary non-DB tasks where production DB SHA checks are not required unless
  the Task Card asks for them;
- DB/schema-risk tasks with no production DB touch, which must explicitly
  declare no production DB touch;
- read-only production DB inspection, which must record observed SHA evidence
  and no mutation;
- authorized production DB mutation, which still requires explicit
  authorization, backup evidence and before/after SHA evidence.

Warning: PM-side compact memory still says the next expected hardening task is
`FH-026`, while the explicit Task Card is `FH-032` and the main repo history
already contains later accepted FH tasks. Main repo Hot context and the explicit
Task Card were used as higher-priority sources of truth.

## Files Changed

- `AGENTS.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-032_add-production-db-sha-policy-for-db-risk-tasks_report.md`

## Evidence

Pre-work `git status --short`:

```text
(no output)
```

Preflight:

```text
$ .venv/bin/python scripts/project_gate.py preflight
working_directory: /opt/jc-coach
branch: agentdev
git status --short -uall: (no output)
production DB SHA:
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Changed-files gate:

```text
$ .venv/bin/python scripts/project_gate.py changed
changed/untracked files:
 M AGENTS.md
 M docs/project_management/AGENT_WORKFLOW.md

activated guardians:
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR
```

Required-checks gate:

```text
$ .venv/bin/python scripts/project_gate.py required-checks
mandatory local gate expectations:
- .venv/bin/python scripts/project_gate.py preflight
- .venv/bin/python scripts/project_gate.py changed
- .venv/bin/python scripts/project_gate.py required-checks
- .venv/bin/python scripts/project_gate.py postflight
- git diff --check

activated guardians:
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR
```

Postflight before report creation:

```text
$ .venv/bin/python scripts/project_gate.py postflight
git diff --stat:
AGENTS.md                                  | 16 +++++++++++++++-
docs/project_management/AGENT_WORKFLOW.md | 26 ++++++++++++++++++++++++--
2 files changed, 39 insertions(+), 3 deletions(-)

changed/untracked files:
 M AGENTS.md
 M docs/project_management/AGENT_WORKFLOW.md

activated guardians:
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR

production DB SHA:
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Final changed-files gate after report creation:

```text
$ .venv/bin/python scripts/project_gate.py changed
changed/untracked files:
 M AGENTS.md
 M docs/project_management/AGENT_WORKFLOW.md
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-032_add-production-db-sha-policy-for-db-risk-tasks_report.md

activated guardians:
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR
```

Final postflight after report creation:

```text
$ .venv/bin/python scripts/project_gate.py postflight
changed/untracked files:
 M AGENTS.md
 M docs/project_management/AGENT_WORKFLOW.md
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-032_add-production-db-sha-policy-for-db-risk-tasks_report.md

activated guardians:
DOCUMENTATION_STEWARD
PM_ORCHESTRATOR

production DB SHA:
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Explicit read-only SHA evidence:

```text
$ sha256sum data/cs2_coach.db
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Diff whitespace check:

```text
$ git diff --check
(no output; exit 0)
```

## DB SHA Status

- Production DB touched: no.
- Production DB mutated: no.
- Backup required: no, because no production DB mutation was authorized or
  performed.
- Read-only SHA evidence collected: yes, via project gate preflight/postflight
  and explicit `sha256sum data/cs2_coach.db`.
- Observed SHA:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.

## Safety Declarations

- Code changed: no.
- Tests changed: no.
- Schema artifacts, migrations, baselines or startup schema behavior changed:
  no.
- Copied DB work: no.
- Production DB mutation: no.
- Live Steam/Valve import: no.
- Parser/evaluator/manual evaluator jobs: no.
- Service, deploy, systemd or nginx changes: no.
- Package/dependency changes: no.
- Generated app reports: no.
- `git add`, commit or push: no.
- Forbidden actions detected: false.

## Checks Run

| Check | Result | Notes |
|---|---|---|
| `git status --short` before edits | PASS | Clean; no output. |
| `.venv/bin/python scripts/project_gate.py preflight` | PASS | Clean worktree; production DB SHA observed read-only. |
| `.venv/bin/python scripts/project_gate.py changed` | PASS | Final changed-file output shows only the two scoped policy docs and the allowed FH-032 report. |
| `.venv/bin/python scripts/project_gate.py required-checks` | PASS | Required docs-safe checks and guardians identified. |
| `sha256sum data/cs2_coach.db` | PASS | Read-only SHA evidence collected. |
| `git diff --check` | PASS | No whitespace errors. |
| `.venv/bin/python scripts/project_gate.py postflight` | PASS | Final postflight shows the two scoped policy docs plus the allowed FH-032 report; Documentation Steward and PM Orchestrator guardians active. |
| Allowed-file/control-plane review | PASS | Changed files are within the Task Card allowed list and explicit governance/control-plane scope. |

## Checks Skipped

- Full local quality gate: skipped; Task Card states it is not required unless
  code, scripts or tests change, and this task changed docs only.
- Full pytest: skipped; Task Card states it is not required for this docs-only
  task. Known full-suite pytest stall remains unresolved and is not claimed
  fixed.
- Ruff: skipped; Task Card states it is not required because no code, scripts
  or tests changed.
- Runtime/app smoke: skipped; not authorized or relevant to policy-only docs.
- Service restart/smoke: skipped; service/deploy changes were not authorized.
- Import/parser/evaluator jobs: skipped; not authorized.

## Docs Update Checklist

- Hot/current status docs: checked; no update required. This task changes
  reporting policy, not current product status.
- WP registry/status/handoff docs: checked; no update required. No WP status,
  roadmap state or handoff bootstrap state changed.
- Navigation docs: checked; no update required. No new canonical/navigation doc
  was created; the report is in the existing task report folder.
- Task-relevant domain docs: checked and updated. `AGENTS.md` and
  `AGENT_WORKFLOW.md` now carry the DB SHA evidence policy.
- Documentation Steward: checked and completed for scoped governance docs.
  No broad docs audit was performed.
- Deferred docs follow-up: none.

## Blockers

None.

## Next WP

PM/user review of FH-032. Next task selection remains PM-owned; Executor did
not choose or start follow-up work.
