# FH-014 Mark Historical/Archived Docs As Non-Current Sources Report

Date: 2026-07-07.

## Result

Verdict: PASS

FH-014 completed the scoped documentation currency pass. Historical,
superseded or supporting docs in the allowed file list now have clear
top-of-file blocks saying they are not current product, roadmap, workflow or
source-of-truth documents. Navigation/classification docs were aligned with
those headers.

## Scope

Task type: Documentation / Foundation Hardening / Docs Currency.

Scope executed:

- Added or normalized short top-of-file status/pointer blocks on allowed
  historical/supporting docs.
- Updated `docs/project_management/DOCS_INDEX.md` and
  `docs/project_management/DOCS_MAP.md` only for classification/navigation
  alignment.
- Preserved historical body content.
- Created this FH-014 task report.

Out of scope and not performed:

- No product code, tests, DB files, generated data, service/deploy config or
  package state changes.
- No physical archive, delete, move, rename or broad legacy cleanup.
- No readiness gate status changes and no major CS2 feature work.

## Files Changed

- `docs/CURRENT_MILESTONE.md`
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md`
- `docs/PRODUCT_EXECUTION_STRATEGY.md`
- `docs/FEATURE_ROADMAP_SCORING.md`
- `docs/METRICS_ROADMAP_SCORING_RU.md`
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md`
- `docs/DEMO_DEEP_PARSER_TZ_RU.md`
- `docs/DEMO_STORAGE_TZ.md`
- `docs/STEAM_MATCH_DATES_RU.md`
- `docs/project_management/DOCS_INDEX.md`
- `docs/project_management/DOCS_MAP.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-014_mark-historical-archived-docs-non-current-sources_report.md`

## Diff Summary

- Added non-current status/pointer blocks to the remaining allowed
  historical/supporting docs that could be mistaken for current truth.
- Replaced stale pointers to `docs/PROJECT_CONTROL.md`,
  `docs/CURRENT_MILESTONE.md` and `docs/ROADMAP.md` as governing current
  priorities with pointers to the current canonical hierarchy:
  `AGENTS.md`, `docs/CURRENT_STATUS.md`,
  `docs/project_management/WP_REGISTRY.md`,
  `docs/project_management/VERSION_ROADMAP.md`,
  `docs/project_management/AGENT_WORKFLOW.md`,
  `docs/project_management/DOCS_INDEX.md` and
  `docs/project_management/DOCS_MAP.md`.
- Kept old body content intact except for top-of-file status/pointer blocks.
- Updated navigation/classification entries for the changed docs.

## Historical/Non-Current Docs Marked

- `docs/CURRENT_MILESTONE.md` - historical/superseded milestone evidence.
- `docs/NEXT_100_PERCENT_IMPLEMENTATION_PLAN.md` - historical/superseded
  implementation plan.
- `docs/PRODUCT_EXECUTION_STRATEGY.md` - historical/superseded strategy memo.
- `docs/FEATURE_ROADMAP_SCORING.md` - supporting/historical scoring evidence.
- `docs/METRICS_ROADMAP_SCORING_RU.md` - supporting/historical metric scoring
  evidence.
- `docs/AI_RECOMMENDATIONS_AIM_EXECUTION_PLAN_RU.md` - historical/completed
  recommendation and AI plan.
- `docs/DEMO_DEEP_PARSER_TZ_RU.md` - supporting/historical parser context.
- `docs/DEMO_STORAGE_TZ.md` - supporting/historical demo-storage plan.
- `docs/STEAM_MATCH_DATES_RU.md` - supporting Steam/import date policy, not
  current source-of-truth.

## Docs Update Checklist

- Hot/current status docs: `docs/CURRENT_STATUS.md` was read as Hot context and
  intentionally not changed; FH-014 did not change current state.
- WP registry/status/handoff docs: `docs/project_management/WP_REGISTRY.md` and
  `docs/HANDOFF.md` were read as required Hot/new-session context and
  intentionally not changed; FH-014 did not create, close or re-sequence WPs.
- Navigation docs: `docs/project_management/DOCS_INDEX.md` and
  `docs/project_management/DOCS_MAP.md` were updated to match the changed
  classifications.
- Task-relevant domain docs: allowed historical/supporting roadmap, metrics,
  AI/recommendation, parser, storage and Steam date docs were marked
  non-current at top of file.
- Documentation Steward: applied for this docs-currency task; no full-docs
  audit or physical archiving was performed.
- Deferred docs follow-up: no executor-selected follow-up. Return to PM/user
  for the next explicit foundation-hardening task card.

## Tests/Checks Run

- `git status --short` before edits: PASS; clean output.
- `.venv/bin/python scripts/project_gate.py changed`: PASS.
  - Before report creation it listed only the scoped docs changed by FH-014.
  - After report creation it listed the same scoped docs plus this FH-014
    report file.
  - Activated guardians: `METRICS_GUARDIAN`, `PM_ORCHESTRATOR`.
- `sha256sum data/cs2_coach.db`: PASS; read-only SHA recorded below.
- `git diff --check`: PASS; no whitespace errors.

Full pytest/Ruff were not required by the docs-only task card and were not run.

## DB/Import/Runtime/Service Safety

- Production DB was not mutated.
- No schema or generated data was changed.
- No live Steam/Valve import was run.
- No parser jobs were run.
- No evaluator or manual evaluator jobs were run.
- No app/service/runtime process was started, stopped or restarted.
- No nginx/systemd/deploy config was edited.
- No package install was performed.
- No `git add`, commit, push or staging action was performed.
- No raw demos, uploads or backups were moved, deleted, renamed, compressed or
  archived.

## Production DB SHA

`2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db`

## Residual Risks

- Historical body text remains in the marked docs by design; the new status
  blocks and navigation classifications are the intended guardrail.
- Other historical/cold docs outside the FH-014 allowed file list may still
  contain old wording, but they were outside this task's scope and remain
  bounded by Hot/Warm/Cold context policy.

## Next Recommended Task

No executor-selected task. Return to PM/user for the next explicit
foundation-hardening task card.

## Stop Conditions Encountered

None.
