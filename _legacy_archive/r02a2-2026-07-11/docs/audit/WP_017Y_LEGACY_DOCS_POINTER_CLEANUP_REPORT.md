# WP-017Y Legacy Docs Pointer Cleanup Report

## 1. Summary

WP-017Y performed the Stage A no-risk legacy documentation pointer cleanup
recommended by WP-017X. The pass added or updated short status/pointer blocks
and corrected stale source-of-truth wording in legacy docs without deleting,
moving, archiving or rewriting historical content.

The cleanup keeps the current hierarchy intact: `AGENTS.md`,
`docs/CURRENT_STATUS.md`, `docs/project_management/WP_REGISTRY.md`,
`docs/HANDOFF.md` for new sessions, `docs/DECISIONS.md` for durable decisions,
Warm docs by task relevance, and old audits/prompts/plans as evidence only.

## 2. Preflight

- Path: `/opt/jc-coach`
- Branch: `main`
- Git status before work: clean
- Latest commits before work:
  - `dcb9239 (HEAD -> main, origin/main) Add legacy documentation currency snapshot`
  - `344739d Add task type profiles and prompt contract`
  - `00726c4 Add repo-native agent workflow and docs steward`
  - `b0d4a1c Add project operating protocol and master WP checklist`
  - `17e65a6 Compact current status and handoff governance docs`
  - `db85f30 Repair governance entrypoints and document match mode deferral`
  - `6514c80 Diagnose match mode classification limits`
  - `e96864c Repair WP registry governance`

## 3. Files Changed

| Path | Previous risk | Change made | Final classification |
|---|---|---|---|
| `docs/PROJECT_CONTROL.md` | Claimed canonical/top source and listed old entrypoints/roadmap docs too strongly. | Added supporting-reference status block; changed top wording so Hot context wins; updated working rules to use normal Hot context; softened roadmap/version references. | SUPPORTING |
| `README.md` | Pointed readers to `PROJECT_CONTROL.md` as canonical source. | Replaced top pointer with operator-entrypoint status and current Hot-context/docs navigation references. | SUPPORTING |
| `docs/ROADMAP.md` | Old roadmap with stale `v0.7-prep` framing could be mistaken for current roadmap. | Added historical/archive-candidate status block pointing to `WP_REGISTRY.md` and `VERSION_ROADMAP.md`. | ARCHIVE_CANDIDATE |
| `docs/VERSION_MAP.md` | Old version table with stale version truth. | Added historical/archive-candidate status block pointing to `CURRENT_STATUS.md`, `WP_REGISTRY.md` and `VERSION_ROADMAP.md`. | ARCHIVE_CANDIDATE |
| `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md` | Large old playbook claimed source-of-truth style workflow. | Added historical/archive-candidate status block pointing to current workflow and Hot context. | ARCHIVE_CANDIDATE |
| `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md` | Old handoff manual with stale version/workflow framing. | Added historical/archive-candidate status block pointing to current handoff, workflow and WP registry. | ARCHIVE_CANDIDATE |
| `docs/NON_STOP_DEVELOPMENT_PROMPTS.md` | Old prompt pack referred to obsolete `AGENT.md`/`PROJECT_CONTROL.md` and included commit/push/server instructions. | Replaced header/pointer with historical/archive-candidate status block pointing to `AGENT_WORKFLOW.md`, `AGENTS.md` and `WP_REGISTRY.md`. | ARCHIVE_CANDIDATE |
| `docs/agents/PM_ORCHESTRATOR.md` | Activation paths listed `AGENT.md` as if active and escalation referenced `PROJECT_CONTROL.md` too narrowly. | Activation path now prefers `AGENTS.md` and marks `AGENT.md` as a superseded pointer; escalation now references Hot context and task-relevant Warm governance docs. | SUPPORTING |
| `docs/project_management/DOCS_INDEX.md` | Navigation did not fully reflect WP-017X classifications for old roadmap/task/instruction groups. | Updated classifications for `PROJECT_CONTROL.md`, `ROADMAP.md`, `VERSION_MAP.md`, old curation docs, old prompt pack, `docs/tasks/*` and `instructions/*`. | SUPPORTING navigation |
| `docs/project_management/DOCS_MAP.md` | Map still described old roadmap/version docs too close to source truth and lacked explicit `instructions/*` group row. | Updated classifications and added `instructions/*` group as archive-candidate/supporting historical evidence. | CANONICAL docs map |
| `docs/project_management/WP_REGISTRY.md` | Needed WP-017Y registration. | Registered `WP-017Y` as done after `WP-017X` and before planned `WP-017K`. | CANONICAL |
| `docs/CURRENT_STATUS.md` | Needed latest governance WP update. | Marked WP-017Y as latest completed governance WP and kept WP-017K as next product WP. | CANONICAL |
| `docs/HANDOFF.md` | Needed new-session continuation update. | Marked WP-017Y complete and kept WP-017K as next product WP. | CANONICAL |
| `docs/audit/WP_017Y_LEGACY_DOCS_POINTER_CLEANUP_REPORT.md` | WP evidence required. | Created this report. | SUPPORTING evidence |

## 4. Files/Groups Intentionally Not Changed

- `AGENT.md`: already an obsolete pointer to `AGENTS.md`; no need to touch.
- `docs/PROJECT_OS.md`: already has a superseded/historical pointer block.
- `docs/PROJECT_GOVERNANCE.md`: already says it is a governance reference and
  not current project state.
- `docs/README.md`: already points to Hot context and docs navigation.
- `docs/tasks/*`: large historical task-prompt group. Updating every file would
  create a large historical diff; classification is now captured in
  `DOCS_INDEX.md` and `DOCS_MAP.md`.
- `instructions/*`: several files already have historical/deprecated headers,
  but some point to old control docs. The group is now classified in navigation
  as archive-candidate/historical; per-file header normalization can be a
  follow-up if truly needed.
- `docs/audit/*`: evidence history only; no old reports were rewritten.
- Physical archive candidates: no files were moved, deleted or archived.

## 5. Source-Of-Truth Hierarchy After Cleanup

Current hierarchy remains:

1. Explicit current user WP prompt.
2. `AGENTS.md`.
3. `docs/CURRENT_STATUS.md`.
4. `docs/project_management/WP_REGISTRY.md`.
5. `docs/HANDOFF.md` for new sessions.
6. `docs/DECISIONS.md` for durable decisions.
7. Warm docs by task relevance.
8. Audit reports, old prompts and old plans as evidence/history only.

Per-task Hot context remains only:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/project_management/WP_REGISTRY.md`

No Hot context expansion was made.

## 6. Remaining Archive Candidates

- `docs/ROADMAP.md`
- `docs/VERSION_MAP.md`
- `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`
- `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`
- `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`
- `docs/tasks/*`
- `instructions/*`
- `instructions/1.txt`
- Older strategy/scoring docs if future review decides they are no longer
  useful as supporting evidence.

Physical archive remains optional and requires a separate explicit WP.

## 7. What Was Intentionally Not Changed

- No application code changed.
- No DB files, schema or data changed.
- No service, nginx, systemd or deploy runtime config changed.
- No live Steam/Valve import run.
- No parser jobs run.
- No evaluator or manual evaluator jobs run.
- No product logic changed.
- No `v0.9` promotion performed.
- No WP-018 product block changed or closed.
- No archive moves, deletes or document removals performed.
- No `git add`, commit or push performed.

## 8. Documentation Steward Verdict

`PASS_WITH_WARNINGS`

The active governance layer is safer after pointer cleanup, and `WP-017K` can
proceed. Remaining warning: some historical groups still contain old text, but
they are now clearly classified through navigation and must not override Hot
context.

## 9. Next Recommended Step

Proceed to WP-017K.

## 10. Checks

Final check results:

- `git diff --check`: PASS, no output.
- `git diff --stat`: PASS, tracked-doc diff shown:
  `README.md`, `docs/CURRENT_STATUS.md`, `docs/HANDOFF.md`,
  `docs/NON_STOP_DEVELOPMENT_PROMPTS.md`, `docs/PROJECT_CONTROL.md`,
  `docs/ROADMAP.md`, `docs/VERSION_MAP.md`,
  `docs/agents/PM_ORCHESTRATOR.md`,
  `docs/project_management/CS2_AI_COACH_MASTER_CURATION_PLAYBOOK.md`,
  `docs/project_management/CS2_AI_COACH_PROJECT_CURATION_HANDOFF.md`,
  `docs/project_management/DOCS_INDEX.md`,
  `docs/project_management/DOCS_MAP.md`,
  `docs/project_management/WP_REGISTRY.md`; 113 insertions, 56 deletions.
  New untracked WP report is visible in `git status --short`.
- `git status --short`: PASS, only WP-017Y documentation changes are present.
- `python3 scripts/project_gate.py --help`: PASS, read-only help displayed
  available commands `preflight`, `changed`, `required-checks`, `postflight`.
