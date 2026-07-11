# WP-017I0 Add Root AGENTS Project Contract Report

Date: 2026-07-05

## RESULT: CREATED

Root `AGENTS.md` was added now because the project already had strong WP and
governance documentation, but no repository-level Codex operating contract. That
gap increased the risk of future session drift, especially around production DB,
Steam import, parser, raw demo, recommendation and cap-change boundaries.

## Product Version Observed

Current product version remains `v0.8`.

Target remains `v0.9` Real Data Onboarding / Bulk Demo Usage after WP-017I0.

## Evidence Read

- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/PROJECT_CONTROL.md`
- `docs/project_management/WORK_PACKAGE_BACKLOG.md`
- `docs/project_management/ACCEPTANCE_MATRIX.md`
- `docs/project_management/VERSION_ROADMAP.md`
- Latest WP-017 audit reports:
  - `docs/audit/WP_017D_POST_BATCH_ACCEPTANCE_AND_EVALUATION_TRIGGER_DIAGNOSIS.md`
  - `docs/audit/WP_017E_AUTO_EVALUATION_TRIGGER_REPAIR_REPORT.md`
  - `docs/audit/WP_017F_CONTROLLED_PENDING_73_IMPORT_REPORT.md`
  - `docs/audit/WP_017G_POST_BATCH_DATA_INTEGRITY_ACCEPTANCE_REPORT.md`
  - `docs/audit/WP_017H_POST_BATCH_PERFORMANCE_ACCEPTANCE_REPORT.md`

## Why AGENTS.md Was Added Now

WP-017I0 is a documentation/instruction-file-only guardrail before the explicit
WP-017I promotion decision. `AGENTS.md` gives future Codex sessions a concise
root contract that mirrors the current project governance and prevents common
unsafe actions from being inferred as allowed.

## Key Rules Included

- Role split: Codex is executor/engineer; human/user is operator and approval
  authority; WP prompts and project docs define scope.
- Source-of-truth order from current WP prompt through `AGENTS.md`, current docs,
  audit reports and code/tests.
- Hard bans on committing production DB, backups, uploads, raw demos and
  `__pycache__`.
- Production DB mutation requires explicit WP authorization, backup, before/after
  SHA evidence and report.
- Live Steam/Valve import, production parser jobs, manual evaluator, raw demo
  deletion/move/compression, cap raise and persistent app report generation all
  require explicit authorization.
- Git rules: show status first, do not commit unless asked, exclude runtime data,
  and run `git diff --check`.
- Production DB path and schema-change restrictions.
- Steam/import contract: shell service temp env must use
  `/opt/jc-coach/data/tmp`, cap remains `1`, `result_json` is canonical when
  `ImportJob.status` is coarse, and match mode remains unknown without reliable
  persisted metadata.
- Recommendation contract: `#5` survival is accepted active recommendation;
  legacy `#1/#3/#4` must not receive new hard evaluations unless refreshed;
  evaluations need `metric_confidence`; weak metrics stay caveated.
- Reporting requirements and roadmap sequence through `v1.0`.
- Style rule: keep changes small, do not broaden WP, report `BLOCKED` instead of
  improvising unsafe actions.

## Files Changed

- `AGENTS.md` created.
- `docs/PROJECT_CONTROL.md` updated only to point Codex working rules at
  `AGENTS.md` instead of the stale singular `AGENT.md`.
- `docs/audit/WP_017I0_ADD_ROOT_AGENTS_PROJECT_CONTRACT_REPORT.md` created.

## DB SHA

Before work:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

After work:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA unchanged: yes.

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | no |
| production files touched | no |
| live Steam/Valve import run | no |
| demo download run | no |
| parser job run | no |
| manual evaluator run | no |
| persistent app report generated | no |
| schema changed | no |
| cap changed | no |
| raw demos deleted/moved/compressed | no |
| commit made | no |

## Verification

Initial required commands were run:

```text
git status --short
git log --oneline -20 --decorate
sha256sum data/cs2_coach.db
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
```

Final required commands were run:

```text
git diff --check
python3 scripts/project_gate.py postflight
sha256sum data/cs2_coach.db
```

## Blockers

None for WP-017I0.

## Whether WP-017I Promotion Can Proceed

Yes. WP-017I0 created the root Codex contract and did not alter runtime code,
tests, schema, production DB, imports, parser jobs, raw demos, cap or app reports.
WP-017I can proceed as the explicit `v0.9` promotion/block decision WP with the
existing WP-017 warnings carried forward.

## Next WP

`WP-017I Promote Real Data Onboarding To v0.9`.
