# FH-021 Create Mandatory Local Quality Gate Command Report

Result:
Verdict: BLOCKED

Scope:
- Created a single local quality gate command for the standard Executor local
  gate sequence.
- Added focused mocked tests for command ordering, safe pytest environment and
  failure propagation.
- Updated task-relevant testing/workflow docs only.
- Did not broaden into CI provider config, report-policy work, product
  behavior, DB/schema, import/parser/evaluator, service/deploy or readiness
  gate status changes.

Files changed:
- `scripts/local_quality_gate.py`
- `tests/test_local_quality_gate.py`
- `docs/TESTING.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-021_create-mandatory-local-quality-gate-command_report.md`

Diff summary:
- Added `scripts/local_quality_gate.py`, a fixed-sequence local gate wrapper
  that runs:
  - `.venv/bin/python scripts/project_gate.py preflight`
  - `.venv/bin/python scripts/project_gate.py changed`
  - `.venv/bin/python scripts/project_gate.py required-checks`
  - `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`
  - `.venv/bin/ruff check . --no-cache`
  - `git diff --check`
  - `.venv/bin/python scripts/project_gate.py postflight`
- The wrapper prints each subcommand, preserves subprocess output, runs from
  the repo root, returns non-zero when any subcommand fails and keeps
  `PYTHONDONTWRITEBYTECODE=1` in child environments to avoid repo bytecode
  artifacts.
- Added `tests/test_local_quality_gate.py` with focused mocked subprocess
  coverage for ordering, safe pytest environment and failure propagation.
- Updated `docs/TESTING.md` to document the mandatory local gate command and
  the safe full-suite/Ruff commands.
- Updated `docs/project_management/AGENT_WORKFLOW.md` to identify
  `scripts/local_quality_gate.py` as the standard mandatory local gate while
  keeping `scripts/project_gate.py` as the read-only evidence helper.

Local quality gate command:
- Command: `.venv/bin/python scripts/local_quality_gate.py`
- Status: blocked by existing full-suite pytest stall before the wrapper could
  reach Ruff, `git diff --check` and project gate postflight in the full local
  gate run.
- Evidence:
  - Direct run was interrupted after the full pytest phase produced no further
    output for several minutes: exit `130`.
  - Bounded run `timeout 900s .venv/bin/python scripts/local_quality_gate.py`
    timed out: exit `124`.
  - The bounded run completed project gate `preflight`, `changed` and
    `required-checks`, then stalled during:
    `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`.
  - Diagnostic command
    `timeout 180s env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -vv -p no:cacheprovider`
    timed out at:
    `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
- Because the task card requires the new local gate command itself to pass
  locally, FH-021 cannot honestly claim PASS until the full-suite stall is
  resolved or explicitly accepted by PM/User as an unrelated blocking risk.

Docs update checklist:
- Hot/current status docs: not updated; FH-021 did not change current product
  status, roadmap state or readiness gate status.
- WP registry/status/handoff docs: not updated; FH-021 did not change WP
  registry, handoff or promotion state.
- Navigation docs: not updated; no new navigation/index requirement was scoped.
- Task-relevant domain docs: updated `docs/TESTING.md` and
  `docs/project_management/AGENT_WORKFLOW.md` for the mandatory local gate
  command and its relationship to `project_gate.py`.
- Documentation Steward: applicable because task-relevant docs changed; checked
  that the edits do not weaken `AGENTS.md`, the project gate workflow or the
  control-plane protection policy.
- Deferred docs follow-up: if PM accepts the full-suite stall as a separate
  blocker, add/link a follow-up task for the stalled UI test before relying on
  the local gate for PASS claims.

Tests/checks run:
- `git status --short` before edits: clean, no output.
- Context7 pytest documentation lookup: confirmed `-q` quiet mode and
  `-p no:<plugin>` plugin disabling behavior for the required pytest command.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_local_quality_gate.py -q -p no:cacheprovider`: PASS, `3 passed in 0.05s`.
- `.venv/bin/python scripts/local_quality_gate.py`: interrupted after prolonged
  full pytest stall, exit `130`.
- `timeout 900s .venv/bin/python scripts/local_quality_gate.py`: BLOCKED,
  exit `124`, timed out in full pytest.
- `timeout 180s env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -vv -p no:cacheprovider`:
  BLOCKED, exit `124`, stalled at
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
- `.venv/bin/ruff check . --no-cache`: PASS.
- `git diff --check`: PASS.
- `.venv/bin/python scripts/project_gate.py postflight`: PASS; reported
  activated guardians `DOCUMENTATION_STEWARD`, `PM_ORCHESTRATOR` and
  `TEST_GUARDIAN`.
- `sha256sum data/cs2_coach.db`: read-only SHA recorded below.

DB/import/runtime/service safety:
- Production DB touched: no mutation performed.
- Production DB read: yes, read-only SHA only.
- Schema changed: no.
- DB files edited: no.
- Generated data edited: no.
- Live Steam/Valve import run: no.
- Parser jobs run: no.
- Evaluator/manual evaluator jobs run: no.
- Services started/stopped/restarted/modified: no.
- nginx/systemd/deploy config edited: no.
- Packages installed: no.
- CI provider config added: no.
- `git add`, commit or push run: no.
- Final readiness gate marked PASS: no.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK` changed: no.

Production DB SHA:
`2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db`

Residual risks:
- The local gate command exists and focused tests pass, but it is not accepted
  as fully proven because the required full-suite gate run times out in an
  existing UI test.
- Until the full-suite stall is resolved or explicitly risk-accepted, Executor
  tasks still do not have a passing mandatory local gate for PASS claims.
- The diagnostic identified the stall point but did not repair it because
  editing `tests/test_coach_first_ui.py` or product/runtime behavior is outside
  FH-021 allowed files.

Next recommended task:
- Investigate and repair or explicitly risk-accept the full pytest stall at
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`, then rerun
  `.venv/bin/python scripts/local_quality_gate.py` and close FH-021 or a
  follow-up acceptance task.

Stop conditions encountered:
- Required local quality gate command could not complete because the full
  pytest suite stalled in an existing UI test and timed out.
- Repairing that stalled test would require editing files outside the FH-021
  allowed file list.
