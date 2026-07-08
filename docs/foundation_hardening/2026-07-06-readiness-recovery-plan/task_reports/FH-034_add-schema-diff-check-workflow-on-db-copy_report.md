# FH-034 Add Schema Diff/Check Workflow On DB Copy Report

Date: 2026-07-07

Executor verdict: `PASS_WITH_WARNINGS`

## Result

Implemented a copied-DB schema check workflow in `scripts/migration_check_on_copy.sh`.

The workflow now:

- copies the source SQLite DB to an explicit/safe temp target;
- refuses `data/cs2_coach.db` as a copy target;
- protects against target/source and target/production hardlink identity;
- runs startup compatibility only against the copied target;
- verifies the source DB SHA did not change;
- runs `scripts/schema_baseline_gate.py check` against the copied target using
  the FH-030 baseline by default;
- prints `SCHEMA_GATE_RESULT=match` or `SCHEMA_GATE_RESULT=mismatch` plus a
  unified schema diff for drift.

`scripts/schema_baseline_gate.py` now normalizes SQLite `PRAGMA index_list`
ordinal values during comparison so equivalent schemas do not fail because of
non-semantic index-list ordering. Baseline writing remains unchanged.

## Files Changed

- `scripts/migration_check_on_copy.sh`
- `scripts/schema_baseline_gate.py`
- `tests/test_migrations.py`
- `docs/MIGRATIONS.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-034_add-schema-diff-check-workflow-on-db-copy_report.md`

## Evidence

Initial preflight:

```text
git status --short
<clean>
```

Context/docs:

- Used context manifest: yes.
- Read hot context: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
  `docs/project_management/WP_REGISTRY.md`, `docs/HANDOFF.md`.
- Read task-scoped Warm workflow doc: `docs/project_management/AGENT_WORKFLOW.md`.
- External docs lookup: Context7 `/pytest-dev/pytest` for `tmp_path` and
  subprocess/captured-output testing behavior.

Focused migration tests:

```text
.venv/bin/pytest tests/test_migrations.py -q
...........                                                              [100%]
11 passed in 2.36s
```

Shell parsing:

```text
bash -n scripts/migration_check_on_copy.sh
<no output, exit 0>
```

Ruff:

```text
.venv/bin/ruff check . --no-cache
All checks passed!
```

Whitespace/diff check:

```text
git diff --check
<no output, exit 0>
```

Project gate postflight:

```text
.venv/bin/python scripts/project_gate.py postflight
## git diff --stat
docs/MIGRATIONS.md                 | 23 ++++++++++--
 scripts/migration_check_on_copy.sh | 37 ++++++++++++++++++-
 scripts/schema_baseline_gate.py    | 24 +++++++++---
 tests/test_migrations.py           | 76 +++++++++++++++++++++++++++++++++++++-
 4 files changed, 148 insertions(+), 12 deletions(-)

## production DB SHA
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

Final status:

```text
git diff --check
<no output, exit 0>

git status --short
 M docs/MIGRATIONS.md
 M scripts/migration_check_on_copy.sh
 M scripts/schema_baseline_gate.py
 M tests/test_migrations.py
?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-034_add-schema-diff-check-workflow-on-db-copy_report.md
```

Production DB copy/schema evidence:

Command:

```bash
rm -f /tmp/jc-coach-fh034-copy-check.db
SOURCE_DB=data/cs2_coach.db \
TARGET_DB=/tmp/jc-coach-fh034-copy-check.db \
PYTHON=.venv/bin/python \
scripts/migration_check_on_copy.sh
rm -f /tmp/jc-coach-fh034-copy-check.db
```

Output excerpt:

```text
MIGRATION_COPY_CHECK_SOURCE=/opt/jc-coach/data/cs2_coach.db
MIGRATION_COPY_CHECK_TARGET=/tmp/jc-coach-fh034-copy-check.db
MIGRATION_COPY_CHECK_SOURCE_SHA256=2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33
MIGRATION_COPY_CHECK_SOURCE_UNCHANGED=true
MIGRATION_COPY_CHECK_SCHEMA_BASELINE=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json
SCHEMA_GATE_DB=/tmp/jc-coach-fh034-copy-check.db
SCHEMA_GATE_BASELINE=/opt/jc-coach/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json
SCHEMA_GATE_BASELINE_HASH=sha256:df411b3fe66f8e6562494294d2ad5cb825b72be625659730485724010dd3d759
SCHEMA_GATE_CURRENT_HASH=sha256:df411b3fe66f8e6562494294d2ad5cb825b72be625659730485724010dd3d759
SCHEMA_GATE_RESULT=match
MIGRATION_COPY_CHECK_RESULT=ok
```

Mismatch/diff behavior is covered by
`tests/test_migrations.py::test_migration_check_reports_schema_mismatch_from_copy`,
which asserts nonzero exit, `MIGRATION_COPY_CHECK_SOURCE_UNCHANGED=true`,
`SCHEMA_GATE_RESULT=mismatch`, `SCHEMA_GATE_DIFF_BEGIN` and the drift table name
in output.

## Warning

The required aggregate gate did not complete:

```text
.venv/bin/python scripts/local_quality_gate.py
```

It passed preflight, changed-file detection and required-check discovery, then
became silent during the full pytest phase after 37 quiet-progress tests. I
interrupted it after several minutes to avoid leaving a running session.

The mandatory full pytest command also timed out:

```text
env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/bin/pytest tests -q -p no:cacheprovider
.....................................
<exit 124 after timeout>
```

A bounded verbose rerun identified the stall point:

```text
env APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 180 .venv/bin/pytest tests -vv -p no:cacheprovider
...
tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state
<exit 124 after timeout>
```

This task did not change UI code. Because a required aggregate check stalled,
`PASS` is not claimed.

## Safety Declarations

- Production DB mutation: no.
- Production DB read/copy: yes, read-only SHA/copy evidence only.
- Observed production DB SHA:
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- Production DB copy target: `/tmp/jc-coach-fh034-copy-check.db`.
- Production DB copy cleanup: temp copy removed after evidence collection.
- Startup schema behavior changed: no.
- SQLAlchemy models changed: no.
- Migration/baseline artifact changed: no.
- Alembic adoption or migration engine added: no.
- Migration revisions created: no.
- Production migration/schema apply run: no.
- Live Steam/Valve import run: no.
- Parser/evaluator/manual evaluator jobs run: no.
- Service/deploy config changed: no.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` changed: no.
- Persistent app reports generated: no.
- `git add`, commit or push run: no.

## Documentation Steward Check

- `docs/MIGRATIONS.md` was updated because the migration workflow behavior
  changed.
- Hot/current status docs were checked and were not updated because FH-034 adds
  a workflow/check improvement without changing project status, roadmap pause
  state or product behavior.
- Navigation docs were not updated because no new canonical entrypoint was
  created.
- Control-plane docs were not changed.

## Blockers

No implementation blocker remains for the scoped copy/schema workflow.

Residual verification warning: full-suite/local-quality-gate execution stalls at
`tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.

## Next WP

PM/User review of FH-034 output. If the full-suite stall is not already known,
open a narrow follow-up test-stability task for
`tests/test_coach_first_ui.py::test_coach_page_renders_for_authenticated_owner_with_empty_state`.
