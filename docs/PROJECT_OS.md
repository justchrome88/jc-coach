# Project OS

Short entrypoint for any new Codex pass or chat.

## Current State

- Current Product Version: `v0.5`
- Current WP: `WP-014 Import Acceptance`
- Next Target Version: `v0.6`
- Current gate: governance-controlled pass; no product logic or DB mutation without explicit WP authorization.

## Source Of Truth

- Human docs entrypoint: `docs/README.md`
- Human docs index: `docs/project_management/DOCS_INDEX.md`
- Control: `docs/PROJECT_CONTROL.md`
- Current status: `docs/CURRENT_STATUS.md`
- Current milestone: `docs/CURRENT_MILESTONE.md`
- Governance: `docs/PROJECT_GOVERNANCE.md`
- Handoff: `docs/HANDOFF.md`
- Version roadmap: `docs/project_management/VERSION_ROADMAP.md`
- Work package backlog: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance matrix: `docs/project_management/ACCEPTANCE_MATRIX.md`
- Docs map: `docs/project_management/DOCS_MAP.md`
- Testing: `docs/TESTING.md`
- Security: `docs/SECURITY.md`
- Backup/restore: `docs/BACKUP_RESTORE.md`
- Deployment/runtime: `docs/DEPLOYMENT.md`

## Mandatory Workflow

1. Read `AGENT.md`, `docs/PROJECT_CONTROL.md`, `docs/PROJECT_OS.md`, `docs/HANDOFF.md`.
2. Run `python scripts/project_gate.py preflight`.
3. Identify changed paths with `python scripts/project_gate.py changed`.
4. Read activated guardian docs under `docs/agents/`.
5. Read `docs/project_management/WORK_PACKAGE_BACKLOG.md` for active/next WP scope.
6. Run `python scripts/project_gate.py required-checks`.
7. Do the smallest authorized task only.
8. Run safe checks and `python scripts/project_gate.py postflight`.
9. Report DB SHA before/after, tests, live jobs, service restart and commit status.

## Guardians

- `PM_ORCHESTRATOR`: WP scope, version map, handoff, gates.
- `DB_GUARDIAN`: DB files, auth persistence, migrations, contamination risk.
- `RUNTIME_GUARDIAN`: FastAPI/web runtime, service freshness, smoke checks.
- `TEST_GUARDIAN`: test isolation and safe verification.
- `IMPORT_GUARDIAN`: Steam/import/demo parser boundaries.
- `METRICS_GUARDIAN`: metric truth, recommendation evidence, AI output truth.
- `UI_COACH_GUARDIAN`: `/coach` UI honesty and read-only page rendering.

## Start A Codex Pass

```bash
git status --short
git log --oneline -12
sha256sum data/cs2_coach.db
systemctl status jc-coach --no-pager
python scripts/project_gate.py preflight
python scripts/project_gate.py changed
python scripts/project_gate.py required-checks
```

Then read the guardian docs activated by the changed paths.

For roadmap context, read:

- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/DOCS_MAP.md`

For human navigation, start with:

- `docs/README.md`
- `docs/project_management/DOCS_INDEX.md`

## Hand Off To A New Chat

Update `docs/HANDOFF.md` when current state, blocker, DB SHA, runtime status or next WP changes. The final report must name files changed, checks run, DB SHA before/after, live jobs run, production DB touched, service restart status and next recommended WP.
