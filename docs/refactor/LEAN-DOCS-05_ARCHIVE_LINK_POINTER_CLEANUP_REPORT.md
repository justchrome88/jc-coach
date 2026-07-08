# LEAN-DOCS-05 Archive Link Pointer Cleanup Report

Task ID: `LEAN-DOCS-05_ARCHIVE_LINK_POINTER_CLEANUP`

Date: 2026-07-09

Role: Codex Documentation Steward

Mode: docs-only / link-pointer-cleanup / file-backed

## Result

`PASS_WITH_WARNINGS`

Updated Warm process/navigation documentation pointers that still referred to
historical `docs/tasks/*` and `instructions/*` roots after
`LEAN-DOCS-04_ARCHIVE_HISTORICAL_PROCESS_MASS`.

No files were archived, deleted, moved or renamed in this task. No product
status, code, DB/data, runtime, tests, tools, dependencies, services, deploy
config or `/opt/jc-coach-pm` content was changed.

Warning: the requested grep check still reports archive-qualified paths because
preserved archive locations intentionally include the original path segments
under `docs/archive/lean-docs-2026-07-09/from-root/`.

## Changed Files

- `docs/project_management/DOCS_MAP.md`
- `docs/project_management/DOCS_INDEX.md`
- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`
- `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md`
- `docs/DOCUMENTATION_AUDIT.md`
- `docs/PROJECT_CONTROL.md`
- `docs/README.md`
- `docs/refactor/LEAN-DOCS-05_ARCHIVE_LINK_POINTER_CLEANUP_REPORT.md`

## Links Found

Initial allowed grep found `36` matching lines in process/navigation docs:

- `docs/project_management/DOCS_MAP.md`: `5`
- `docs/project_management/DOCS_INDEX.md`: `5`
- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`: `3`
- `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`: `1`
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md`: `1`
- `docs/DOCUMENTATION_AUDIT.md`: `18`
- `docs/PROJECT_CONTROL.md`: `2`
- `docs/README.md`: `1`

## Links Updated

- Replaced generic Cold-context mentions of old task/instruction roots with
  archived historical evidence wording.
- Replaced historical task prompt references with
  `docs/archive/lean-docs-2026-07-09/from-root/docs/tasks/...`.
- Replaced historical instruction artifact references with
  `docs/archive/lean-docs-2026-07-09/from-root/instructions/...`.
- Updated stale archive-candidate language in navigation rows to archived
  historical evidence language.
- Updated one older audit/deprecation-plan line to reflect that LEAN-DOCS-04
  already moved stale instruction artifacts into the archive.

## Links Intentionally Left Unchanged

None as stale unqualified old-path pointers.

Archive-qualified preserved paths were intentionally left in place where the
document benefits from a concrete historical evidence pointer.

## Checks

- Preflight `git status --short`: clean before work.
- Preflight branch: `cona`.
- Preflight HEAD: `5d9cb787379d9c8b00211dd3433db7abab6dc33f`.
- `git diff --check`: `PASS` with no output.
- Allowed link grep:
  `PASS_WITH_WARNINGS`; `30` remaining matches are archive-qualified pointers
  under `docs/archive/lean-docs-2026-07-09/from-root/...`.
- Additional stricter stale-pointer scan excluding archive-qualified preserved
  path segments: `PASS` with no output.
- `git status --short`: expected docs-only modifications and one new report:
  - `M docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md`
  - `M docs/DOCUMENTATION_AUDIT.md`
  - `M docs/PROJECT_CONTROL.md`
  - `M docs/README.md`
  - `M docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`
  - `M docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`
  - `M docs/project_management/DOCS_INDEX.md`
  - `M docs/project_management/DOCS_MAP.md`
  - `?? docs/refactor/LEAN-DOCS-05_ARCHIVE_LINK_POINTER_CLEANUP_REPORT.md`

## Warnings

- The allowed grep pattern is broad and matches archive-qualified paths that
  contain preserved original path segments. These remaining matches are not
  stale active pointers.
- The curation playbook and curation handoff remain historical/superseded
  process documents; this task only repaired scoped pointers and did not do
  broader cleanup.

## Recommended Next Task

Run a narrow docs-navigation archive-index pass only if desired, focused on
making `docs/archive/README.md` or the LEAN-DOCS archive manifest easier to
navigate. Do not broaden into product status, WP restart or additional archive
moves without an explicit task.
