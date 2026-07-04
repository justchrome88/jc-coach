# Documentation README

Human navigation entrypoint for the JC Coach documentation tree.

## Start Here

For a new human review, read in this order:

1. `docs/PROJECT_OS.md` - short operating entrypoint.
2. `docs/HANDOFF.md` - current state and next active WP.
3. `docs/project_management/DOCS_INDEX.md` - human-readable navigation by category.
4. `docs/project_management/VERSION_ROADMAP.md` - version roadmap.
5. `docs/project_management/WORK_PACKAGE_BACKLOG.md` - WP scope, guardians and exit criteria.
6. `docs/project_management/ACCEPTANCE_MATRIX.md` - feature acceptance criteria.

For a Codex/pass, also follow `AGENT.md`, `docs/PROJECT_CONTROL.md`, `docs/PROJECT_GOVERNANCE.md` and the guardian docs under `docs/agents/`.

## Current WP

Current active target remains:

```text
WP-012 DB Contamination Guardrails
Target version: v0.4.2
```

Do not start product work without an explicit WP prompt and the required gate checks.

## Source Of Truth

Top-level control:

- `docs/PROJECT_CONTROL.md`
- `docs/PROJECT_OS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_GOVERNANCE.md`

Roadmap and planning:

- `docs/project_management/VERSION_ROADMAP.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/DOCS_MAP.md`
- `docs/project_management/DOCS_INDEX.md`

Domain truth:

- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/METRICS.md`
- `docs/STEAM_IMPORT.md`
- `docs/RECOMMENDATIONS.md`
- `docs/AI_COACH.md`
- `docs/TESTING.md`
- `docs/BACKUP_RESTORE.md`
- `docs/DEPLOYMENT.md`
- `docs/KNOWN_LIMITATIONS.md`

When documents conflict, follow `docs/PROJECT_CONTROL.md`, then the relevant Project OS / governance / domain source-of-truth document.

## Folders

- `docs/agents/`: guardian role docs and required checks by ownership domain.
- `docs/project_management/`: roadmap, WP backlog, acceptance matrix, docs map and human navigation.
- `docs/audit/`: stage/WP evidence, inventories, reviews, incident diagnoses and deprecation/conflict reports.
- `docs/tasks/`: historical task prompts and stage specs; useful evidence, not the active roadmap.
- `docs/archive/`: archived/supporting material.

## Historical / Supporting Docs

Older strategies, prompt libraries, scoring spreadsheets, stage task specs and full-audit reports are supporting or historical unless `docs/PROJECT_CONTROL.md` explicitly reactivates them. Do not delete, move or rename them without an explicit docs cleanup task.

Use `docs/project_management/DOCS_MAP.md` for ownership/freshness status and `docs/project_management/DOCS_INDEX.md` for human navigation.

## Roadmap And Acceptance

- Roadmap: `docs/project_management/VERSION_ROADMAP.md`
- WP details: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance criteria: `docs/project_management/ACCEPTANCE_MATRIX.md`

