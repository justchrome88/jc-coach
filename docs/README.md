# Documentation README

Human navigation entrypoint for the JC Coach documentation tree.

> Status: Navigation document.
> Do not use this file as current project state.
> Current source of truth: `AGENTS.md`, `docs/CURRENT_STATUS.md`,
> `docs/project_management/WP_REGISTRY.md`.
> For new-session bootstrap, also read `docs/HANDOFF.md`.

## Start Here

For a normal Codex task, use the Hot context defined in `AGENTS.md`:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

For a new-session bootstrap, also read `docs/HANDOFF.md`.

For a human review, use this navigation file to find Warm docs by topic. Do not
read the whole documentation tree by default.

## Current WP

Current product version, current WP and next target live in
`docs/CURRENT_STATUS.md` and `docs/project_management/WP_REGISTRY.md`.

Do not start product work without an explicit WP prompt and the required gate checks.

## Source Of Truth

Hot context:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/HANDOFF.md` for new-session bootstrap

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

When documents conflict, follow the source-of-truth order in `AGENTS.md`: the
current explicit WP prompt, then Hot context, then relevant Warm docs.
Historical docs, audit reports and old prompts are evidence/history, not current
project state.

## Folders

- `docs/agents/`: guardian role docs and required checks by ownership domain.
- `docs/project_management/`: roadmap, WP backlog, acceptance matrix, docs map and human navigation.
- `docs/audit/`: stage/WP evidence, inventories, reviews, incident diagnoses and deprecation/conflict reports.
- `docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/`: archived historical task prompts and stage specs; useful evidence, not the active roadmap.
- `docs/archive/`: archived/supporting material.

## Historical / Supporting Docs

Older strategies, prompt libraries, scoring spreadsheets, stage task specs and full-audit reports are supporting or historical unless `docs/PROJECT_CONTROL.md` explicitly reactivates them. Do not delete, move or rename them without an explicit docs cleanup task.

Use `docs/project_management/DOCS_MAP.md` for ownership/freshness status and `docs/project_management/DOCS_INDEX.md` for human navigation.

## Roadmap And Acceptance

- Roadmap: `docs/project_management/VERSION_ROADMAP.md`
- WP details: `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- Acceptance criteria: `docs/project_management/ACCEPTANCE_MATRIX.md`
