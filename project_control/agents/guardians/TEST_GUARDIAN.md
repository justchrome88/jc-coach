# Test Guardian

## Scope

Protects test isolation, safe verification commands and evidence quality.

## Activation Paths

- `tests/*`
- `pytest.ini`
- `conftest.py`
- `project_docs/operations/TESTING.md`
- test helper scripts

## Forbidden Actions

- Running tests without `APP_ENV=test`.
- Pointing tests at `data/cs2_coach.db`.
- Using tests to start live Steam/import/parser/AI jobs.
- Treating skipped or partial tests as full evidence without naming gaps.

## Required Checks

- `APP_ENV=test .venv/bin/pytest tests -q`
- `.venv/bin/ruff check .`
- `git diff --check`

## Evidence Required

- Test command and result.
- Any warnings/failures/skips.
- Confirmation that production DB/settings were not used.

## Escalation / Blocker Rules

Block if the requested validation cannot run safely without production DB or live external jobs.

