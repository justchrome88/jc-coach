# FH-020 Expand Project Gate Preflight/Postflight Report

Result: PASS
Verdict: PASS

## Scope

Task card: `FH-020 Expand Project Gate Preflight/Postflight`.

Implemented the scoped project gate strengthening in `scripts/project_gate.py`,
added focused tests, and updated the allowed workflow/testing docs. The
2026-07-07 revision did not redo implementation work; it reran the required
checks and closed the previously missing full safe test suite evidence.

Initial `git status --short` before edits: no output; worktree was clean.

Context7 dependency/API docs lookup:

- Resolved `/pytest-dev/pytest`.
- Queried pytest docs for `tmp_path`, `monkeypatch` and `capsys` fixture
  behavior before adding the focused tests.

## Files Changed

- `scripts/project_gate.py`
- `tests/test_project_gate.py`
- `docs/TESTING.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-020_expand-project-gate-preflight-postflight_report.md`

## Diff Summary

Pre-report diff stat:

```text
docs/TESTING.md                           |  20 ++
docs/project_management/AGENT_WORKFLOW.md |  24 ++-
scripts/project_gate.py                   | 328 ++++++++++++++++++++++--------
3 files changed, 279 insertions(+), 93 deletions(-)
```

`tests/test_project_gate.py` is a new untracked allowed file and is not included
in tracked-only `git diff --stat` until staged.

## Project Gate Behavior Changed

- `preflight` now reports working directory, branch, recent decorated commits,
  `git status --short -uall`, required governance file presence and read-only
  production DB SHA.
- Removed the previous service status probe from `preflight`; the gate remains
  read-only and does not inspect or mutate services.
- `changed` now prints status-coded changed/untracked paths and activated
  guardians.
- Guardian inference now includes script/test changes for `TEST_GUARDIAN` and
  docs/control-plane changes for `DOCUMENTATION_STEWARD`.
- `required-checks` now separates mandatory local gate expectations from
  guardian-specific required/recommended checks and adds full local gate
  expectations for code/test/script changes.
- `postflight` now reports diff stat, changed/untracked paths, activated
  guardians, required-check summary, governance file presence and read-only
  production DB SHA.

## Docs Update Checklist

- Hot/current status docs: checked; no update required. FH-020 does not change
  current project status, WP registry state, handoff state or readiness flag.
- WP registry/status/handoff docs: checked; no update required. This task does
  not close the readiness gate, promote a version or alter WP ordering.
- Navigation docs: checked; no update required. No new canonical/navigation doc
  was introduced.
- Task-relevant domain docs: checked and updated. `docs/TESTING.md` and
  `docs/project_management/AGENT_WORKFLOW.md` now describe the strengthened
  project gate workflow.
- Documentation Steward: required and completed for this file-backed hardening
  task because docs/control-plane workflow text changed. The updates do not
  weaken `AGENTS.md`, the control-plane protection policy or readiness
  restrictions.
- Deferred docs follow-up: none for this task's implemented docs; the
  previously missing full-suite execution evidence is now closed.

## Tests/Checks Run

- `git status --short` before edits: PASS, no output.
- Revision `git status --short --untracked-files=all`: PASS, scoped FH-020
  worktree only:

  ```text
   M docs/TESTING.md
   M docs/project_management/AGENT_WORKFLOW.md
   M scripts/project_gate.py
  ?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-020_expand-project-gate-preflight-postflight_report.md
  ?? tests/test_project_gate.py
  ```

- Final `git status --short --untracked-files=all` after report revision:
  PASS, same scoped FH-020 worktree only.

- `.venv/bin/python scripts/project_gate.py preflight`: PASS. Reported branch
  `agentdev`, changed files, governance file presence and production DB SHA
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
  Revision rerun exit code `0`.
- `.venv/bin/python scripts/project_gate.py changed`: PASS. Activated
  `DOCUMENTATION_STEWARD`, `PM_ORCHESTRATOR` and `TEST_GUARDIAN`. Revision
  rerun exit code `0`.
- `.venv/bin/python scripts/project_gate.py required-checks`: PASS. Reported
  mandatory project gate, full pytest, Ruff and `git diff --check`
  expectations for code/test/script changes. Revision rerun exit code `0`.
- `.venv/bin/python scripts/project_gate.py postflight`: PASS. Reported diff
  stat, changed/untracked files, activated guardians, required-check summary,
  governance file presence and production DB SHA. Revision rerun exit code
  `0`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_project_gate.py -q -p no:cacheprovider`:
  PASS, original `5 passed in 0.22s`; revision rerun `5 passed in 0.16s`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`:
  PASS on revision rerun, `216 passed, 1 warning in 8.50s`. Warning:
  `StarletteDeprecationWarning` from
  `.venv/lib/python3.14/site-packages/fastapi/testclient.py:1` about Starlette
  `TestClient` using deprecated `httpx`.
- `.venv/bin/ruff check . --no-cache`: PASS, `All checks passed!`.
- `git diff --check`: PASS before report revision and PASS again after report
  revision, no output.
- `sha256sum data/cs2_coach.db`: PASS,
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db`.

Previous transient blocked evidence, retained for honesty:

- First Executor run
  `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`:
  BLOCKED. The command produced initial progress dots and then no output for
  several minutes; it was interrupted with exit code `130`.
- First Executor diagnostic rerun:
  `timeout 180s env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -vv -p no:cacheprovider`:
  BLOCKED with exit code `124`. It collected 216 tests and reached
  `tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`
  before timing out. The 2026-07-07 exact full-suite rerun completed
  successfully, so this is treated as a transient blocked run, not a remaining
  FH-020 stop condition.

## DB/Import/Runtime/Service Safety

- Production DB mutated: no.
- Production DB schema changed: no.
- DB files edited: no.
- Live Steam/Valve import run: no.
- Parser jobs run: no.
- Evaluator/manual evaluator jobs run: no.
- Services started/stopped/restarted/modified: no.
- nginx/systemd/deploy config edited: no.
- Packages installed: no.
- `git add`, commit or push run: no.
- Persistent app reports generated: no.
- Secret values observed in output: no.

## Production DB SHA

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

The SHA was read only. No before/after DB mutation evidence was required
because no production DB mutation was authorized or performed.

## Residual Risks

- The previous full-suite hang/interrupt was transient on rerun; no product/UI
  repair was performed or required for FH-020 closure.
- The full suite still emits one dependency deprecation warning from
  FastAPI/Starlette `TestClient`; it does not fail the FH-020 required checks.
- `scripts/project_gate.py` remains an evidence/report helper, not an enforcing
  CI/pre-commit gate. FH-P1-003/FH-021+ still need separate enforcement work.

## Next Recommended Task

Proceed to PM review of FH-020 or the next scoped foundation hardening task.
Separate enforcement work remains for FH-P1-003/FH-021+.

## Stop Conditions Encountered

- First Executor run encountered a transient blocked condition:
  `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider`
  hung after initial progress and was interrupted.
- First Executor bounded verbose diagnostic timed out at the coach UI
  empty-state test.
- Revision rerun stop conditions: none. All required checks completed and
  passed.
- No forbidden actions were detected.
