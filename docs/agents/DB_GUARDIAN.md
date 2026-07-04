# DB Guardian

## Scope

Protects production DB, migrations, auth persistence and runtime data from accidental mutation or contamination.

## Activation Paths

- `app/db/*`
- `data/*.db`
- `app/services/auth.py`
- `docs/BACKUP_RESTORE.md`
- `docs/MIGRATIONS.md`
- migration scripts or schema inventory files

## Forbidden Actions

- Mutating `data/cs2_coach.db` without explicit authorization.
- Running tests against production DB.
- Applying migrations or schema helpers to production DB during governance/tooling work.
- Editing DB files directly.
- Running import/parser/Steam jobs that write to production DB.

## Required Checks

- `sha256sum data/cs2_coach.db` before and after.
- `APP_ENV=test .venv/bin/pytest tests -q` for code changes that could affect DB safety.
- Migration checks only on temp/copy DB when migration scope is explicitly active.
- `git diff --check`.

## Evidence Required

- DB SHA before/after.
- Statement whether production DB was touched.
- Statement whether schema/data migrations ran.
- Test DB isolation evidence.

## Escalation / Blocker Rules

Block if a task requires production DB mutation but lacks explicit user approval, backup/restore evidence or rollback instructions.

