# Import Guardian

## Scope

Protects Steam import, manual demo import, parser jobs, upload routes and service-bot boundaries.

## Activation Paths

- `app/services/steam_integration.py`
- `app/services/demo_parser.py`
- import/upload routes
- Steam/import/parser docs and tests
- `data/uploads/*`
- `data/incoming_demos/*`

## Forbidden Actions

- Running live Steam calls without explicit authorization.
- Running production import/parser jobs during governance/tooling work.
- Downloading or parsing real demos unless the WP allows it.
- Storing Steam personal credentials, refresh tokens or Steam Guard data.
- Advancing Steam cursor outside an authorized import flow.

## Required Checks

- Mocked/import-safe tests only unless live work is explicitly authorized.
- DB SHA before/after when import code or runtime DB could be affected.
- Review `docs/STEAM_IMPORT.md` for Steam scope.
- `git diff --check`.

## Evidence Required

- Statement whether live Steam/import/parser jobs ran.
- Cursor mutation status when Steam paths are involved.
- DB touch status.
- Mock/live boundary used for tests.

## Escalation / Blocker Rules

Block if a task would require live Steam, demo download, parser execution or production DB writes without explicit permission.

