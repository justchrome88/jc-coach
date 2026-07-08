# FH-124R-02A Diagnose Recurring H1 Full-Suite Timeout Report

Date: 2026-07-08

Task: `FH-124R-02A Diagnose recurring H1 full-suite timeout`

Task type: Audit / Review / Discovery - test/gate diagnostic only

Mode: Review-only, bounded commands, fail-closed

## Verdict

Executor verdict: `PASS`

Diagnostic confidence: `PASS_WITH_WARNINGS`

H1 final readiness passed: `NO`

The recurring timeout was not reproduced in this direct Executor session. Every
bounded direct full-suite path completed in about 12 seconds with the same 250
tests passing. The only confirmed timeout evidence remains the H1
agent-cycle/final-gate context:

- `FH-120_124`: quiet full suite stalled after initial quiet output and was
  interrupted with exit `130`.
- `FH-124R-01`: verbose full suite, original quiet H1 command and local quality
  gate all passed outside the failed H1 run.
- `FH-120_124R-02`: mandatory quiet full suite timed out under
  `timeout 420s` with exit `124` inside the agent-cycle rerun.

Most likely diagnosis: the timeout is non-deterministic and context-sensitive,
isolated to the PM/agent-cycle final-gate execution path observed so far, not a
deterministic hanging test, pytest collection issue, pytest cache issue, quiet
mode issue, capture-mode issue, console-entrypoint issue, PTY issue or local
quality gate wrapper issue in the current direct Executor context.

The quiet progress marker is still useful: the historical stall occurred after
37 dots, which corresponds to the transition into
`tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
However, that test passed repeatedly here and appeared in the slowest-test list
at about `0.11s`, so it is a symptom marker rather than a proven root cause.

## Context Used

Hot/new-session context read:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/HANDOFF.md`

Task-specific context read:

- `/opt/jc-coach-pm/outbox/2026-07-08_FH-124R-02A_task-card.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-01_recover-full-suite-pytest-final-gate-stall_report.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-120_124R-02_h1-final-readiness-rerun_report.md`
- `/opt/jc-coach-pm/reviews/2026-07-08_FH-120_124R-02_review.md`
- `/var/tmp/jc-coach-agent-runs/2026-07-08_155430_agent_cycle/summary.md`
- `/var/tmp/jc-coach-agent-runs/2026-07-08_155430_agent_cycle/state.env`
- `/var/tmp/jc-coach-agent-runs/2026-07-08_155430_agent_cycle/review_evidence.md`
- `/opt/jc-coach-pm/.agent_cycle_cache/current/preflight_context.md`

External docs:

- Context7 lookup for `/pytest-dev/pytest` confirmed that `-q` changes
  verbosity, `-v/-vv` increases reporting, `-s` disables capture,
  `--durations=N` reports slow tests, and pytest has faulthandler timeout
  support. These options do not reduce the collected test set by themselves.

## Environment Snapshot

Commands were run from `/opt/jc-coach`.

| Command | Exit | Evidence |
|---|---:|---|
| `env \| sort` | `0` | Key entries: `CODEX_CI=1`, `PWD=/opt/jc-coach`, `USER=root`, `SUDO_USER=jc`, `PATH` starts with Codex standalone paths. No `APP_ENV`, `PYTEST_*` or `DATABASE_URL` override was present in the baseline environment. Full env output was not copied into this report to avoid unnecessary secret exposure. |
| `pwd` | `0` | `/opt/jc-coach` |
| `whoami` | `0` | `root` |
| `ulimit -a` | `0` | Open files `1024`; max user processes `4813`; stack `8192`; CPU/memory/file size unlimited. |
| `ps -ef \| grep -E 'pytest\|python\|agent_cycle\|codex' \| grep -v grep` | `0` | Before diagnostics: service uvicorn process, current `codex --sandbox danger-full-access --ask-for-approval never -C /opt/jc-coach`, no lingering pytest except the concurrent version probe. After diagnostics: service uvicorn and current Codex only; no pytest/agent-cycle process left running. |
| `git status --short` | `0` | Clean before report work; no output. |
| `git branch --show-current && git rev-parse HEAD` | `0` | Branch `agentdev`, HEAD `56ac86f1002253bb346f1434778b9c4625b4dab7`. |
| `.venv/bin/python --version` | `0` | `Python 3.14.4` |
| `.venv/bin/python -m pytest --version` | `0` | `pytest 9.1.1` |
| `python - <<'PY' ...` | `127` | Bare `python` is not available on PATH. |
| `.venv/bin/python - <<'PY' ...` | `0` | Python `3.14.4`, platform `Linux-7.0.0-27-generic-x86_64-with-glibc2.43`. |

## Agent-Cycle Comparison

Confirmed failing context from
`/var/tmp/jc-coach-agent-runs/2026-07-08_155430_agent_cycle`:

- `RUN_ID=2026-07-08_155430_agent_cycle`
- `CODEX_SANDBOX=workspace-write`
- `PM_CREATE` ran before Executor and wrote/used the PM context manifest.
- `EXECUTOR_VERDICT=FAIL`
- failing Executor report:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-120_124R-02_h1-final-readiness-rerun_report.md`
- failing command:
  `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 420s .venv/bin/pytest tests -q -p no:cacheprovider`
- failure:
  emitted initial quiet output `.....................................`, then timed out with exit `124`.

Current direct diagnostic context:

- current Codex process:
  `codex --sandbox danger-full-access --ask-for-approval never -C /opt/jc-coach`
- no PM_CREATE phase or active agent-cycle parent process;
- main repo already includes accepted commit
  `56ac86f1002253bb346f1434778b9c4625b4dab7`;
- every direct full-suite variant passed.

The available evidence therefore isolates the observed recurring timeout to
agent-cycle final-gate runs so far. It does not prove that `workspace-write`,
PM_CREATE, model routing, manifest activity or the agent-cycle parent process
is individually causal; it proves only that direct Executor contexts repeatedly
do not reproduce the timeout while H1 agent-cycle final-gate contexts did.

## Command Evidence

Required and addendum-requested commands:

| Command | Timeout | Exit | Time | Evidence |
|---|---:|---:|---:|---|
| `.venv/bin/python scripts/project_gate.py preflight` | none | `0` | n/a | Branch `agentdev`; clean status; production DB SHA read-only evidence `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`. |
| `.venv/bin/python scripts/project_gate.py changed` | none | `0` | n/a | `(none)` changed/untracked before report; activated guardian `PM_ORCHESTRATOR`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 120s .venv/bin/pytest --collect-only tests -q -p no:cacheprovider` | `120s` | `0` | `0:00.90` | `250 tests collected in 0.29s`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 180s .venv/bin/pytest tests -vv -ra --durations=50 -p no:cacheprovider` | `180s` | `0` | `0:12.31` | `250 passed, 1 warning in 11.49s`; slowest calls were migration-copy checks at `0.63s-0.66s`; suspected coach-first UI test was `0.11s`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 timeout 120s .venv/bin/pytest tests -q -p no:cacheprovider` | `120s` | `0` | `0:12.41` | `250 passed, 1 warning in 11.58s`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 timeout 120s .venv/bin/pytest tests -vv -s -p no:cacheprovider --durations=20` | `120s` | `0` | `0:12.21` | `250 passed, 1 warning in 11.32s`; suspected coach-first UI test `0.11s`. |
| `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 timeout 120s .venv/bin/python -m pytest tests -q -p no:cacheprovider` | `120s` | `0` | `0:12.31` | `250 passed, 1 warning in 11.38s`. |
| `timeout 180s .venv/bin/python scripts/local_quality_gate.py` | `180s` outer | `0` | `0:21.12` | `LOCAL_QUALITY_GATE=PASS`; full safe pytest substep `250 passed, 1 warning in 11.79s`; Ruff and `git diff --check` passed. |
| PTY probe: `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 timeout 120s .venv/bin/pytest tests -q -p no:cacheprovider` | `120s` | `0` | `0:12.21` | `250 passed, 1 warning in 11.38s`; terminal allocation alone did not reproduce the timeout. |
| Exact quiet rerun without faulthandler: `env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 120s .venv/bin/pytest tests -q -p no:cacheprovider` | `120s` | `0` | `0:12.31` | `250 passed, 1 warning in 11.51s`. |
| `.venv/bin/python scripts/project_gate.py postflight` | none | `0` | n/a | Only scoped untracked report path; activated guardians `DOCUMENTATION_STEWARD`, `PM_ORCHESTRATOR`; production DB SHA read-only evidence unchanged. |
| `git diff --check` | none | `0` | n/a | No output. |
| `git status --short` | none | `0` | n/a | `?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md`. |

No quiet command hung during this task, so no pre-kill `pstree` evidence was
available to capture. The process snapshot after diagnostics found no remaining
pytest process.

## Comparison Findings

| Dimension | Finding |
|---|---|
| Quiet `-q` only | Not supported. Quiet direct full suite passed repeatedly. |
| Non-verbose capture mode | Not supported. Captured verbose and quiet direct modes passed. |
| `-s` capture disabled | Not causal in direct context. Verbose `-s` passed; captured verbose also passed. |
| `pytest` console script vs `python -m pytest` | Not supported. Both passed. |
| Pytest cache | Not supported. All commands used `-p no:cacheprovider` where required. |
| PTY vs non-PTY | Not supported. Both passed. |
| `local_quality_gate.py` wrapper | Not supported. Wrapper passed and includes the full quiet pytest suite. |
| After prior PM_CREATE/manifest activity | Plausible context marker, not individually proven causal. The failing run had PM_CREATE/context manifest phases; this direct run did not. |
| Agent-cycle/Codex background context | Best-supported isolation. Confirmed timeouts are in H1 agent-cycle final-gate history; direct Executor diagnostics pass. |

## Safe Final-Gate Adjustment Recommendation

Do not remove or skip `pytest tests -q -p no:cacheprovider`.

For the next H1 rerun, preserve full-suite coverage but make the canonical
agent-cycle final-gate command more observable:

```bash
env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 timeout 420s \
  .venv/bin/pytest tests -vv -ra --durations=50 -p no:cacheprovider
```

Then also run the accepted local CI-equivalent wrapper:

```bash
timeout 420s .venv/bin/python scripts/local_quality_gate.py
```

Rationale:

- The verbose command covers the same full `tests` suite and does not weaken
  coverage.
- It gives the last completed test name if the agent-cycle context stalls.
- `PYTHONFAULTHANDLER=1` improves crash/deadlock evidence without changing the
  test set.
- `scripts/local_quality_gate.py` preserves the accepted local gate discipline
  and has heartbeats around each step.
- The existing quiet command should remain documented as part of the gate
  history; future tasks should not claim final readiness from a reduced test
  set.

If PM/user requires the exact quiet command to remain a mandatory separate
check, run it only after the verbose full suite and local gate pass, and if it
times out again, classify the failure as an agent-cycle quiet-command
observability/runner issue rather than evidence of uncovered test failure,
pending PM/user acceptance.

## Files Changed

- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md`

No product code, tests, scripts, config, status docs, risk registers,
readiness-gate docs, PM workspace files, DB/schema files or deploy/service
files were edited.

## Docs Update Checklist

| Checklist item | Status | Reason |
|---|---|---|
| Hot/current status docs | `checked; no update required` | Task card forbids status updates; H1 remains failed. |
| WP registry/status/handoff docs | `checked; no update required` | No readiness unlock, no H2, no WP-018 restart. |
| Navigation docs | `checked; no update required` | Existing task-report folder used. |
| Task-relevant domain docs | `checked; no update required` | Readiness/test docs reviewed only; edits forbidden except this report. |
| Documentation Steward | `checked; no update required` | Scoped report-only task. |
| Deferred docs follow-up | `deferred` | PM/user may choose whether to update gate docs after accepting this diagnostic. |

## Safety Declarations

Forbidden actions detected: `false`.

- Implementation changed: `NO`.
- Product code/tests/scripts/config changed: `NO`.
- Docs/status/risk-register edits made except this report: `NO`.
- Production DB mutation: `NO`.
- Production DB copy: `NO`.
- Schema mutation, migration artifact edit, startup schema behavior change or
  migration-engine adoption: `NO`.
- Production DB SHA observed read-only by `project_gate.py preflight`:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Live Steam/Valve import: `NO`.
- Parser job, evaluator job or manual evaluator job: `NO`.
- Demo download, decompression, raw-demo move/delete/compression or upload
  operation: `NO`.
- Deploy/service/nginx/systemd change or restart: `NO`.
- Package installation: `NO`.
- Secrets printed in this report: `NO`.
- `git add`, commit or push: `NO`.
- H2 run: `NO`.
- WP-018 restarted: `NO`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK=YES` set: `NO`.

## Blockers

No blocker prevented completing the diagnostic report. The root cause is not
fully proven because the timeout did not reproduce outside the H1 agent-cycle
final-gate context.

## Discovery Result

```yaml
discovery_result:
  completeness_estimate: "High for direct pytest/local-gate behavior; medium for exact agent-cycle root cause because the timeout did not reproduce in this Executor context."
  missing_items_found: true
  followup_required: true
  followup_tasks_recommended:
    - proposed_id: "FH-124R-02B"
      title: "Rerun H1 final gate with verbose faulthandler full suite"
      reason: "The recurring timeout is isolated to agent-cycle final-gate context so far; a verbose/faulthandler full-suite command preserves coverage while exposing the last completed test if the agent-cycle stalls again."
      risk: "P1"
      suggested_scope: "tests"
      needs_user_decision: true
    - proposed_id: "FH-124R-02C"
      title: "Add agent-cycle timeout process snapshot"
      reason: "If PM wants exact causal proof, the agent-cycle runner should capture ps/pstree and optionally a faulthandler-triggered traceback before killing a timed-out pytest process."
      risk: "P2"
      suggested_scope: "config"
      needs_user_decision: true
```

## Machine Summary

```text
EXECUTOR_VERDICT=PASS
EXECUTOR_REPORT_PATH=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-124R-02A_diagnose-recurring-h1-full-suite-timeout_report.md
H1_FINAL_READINESS_PASSED=false
H2_REMAINS_BLOCKED=true
WP_018_REMAINS_BLOCKED=true
MAJOR_CS2_WORK_REMAINS_BLOCKED=true
FORBIDDEN_ACTIONS_DETECTED=false
NEEDS_USER=true
```
