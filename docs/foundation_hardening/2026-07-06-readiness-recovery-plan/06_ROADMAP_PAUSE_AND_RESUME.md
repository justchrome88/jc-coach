# Roadmap Pause And Resume

Date: 2026-07-06.

Canonical roadmap sources:

- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/project_management/VERSION_ROADMAP.md`

Historical roadmap source:

- `docs/ROADMAP.md` is explicitly historical/archive-candidate and must not be
  used as current roadmap truth.

## Temporarily Frozen CS2 Tasks

- Unrestricted major WP-018 / CS2 feature expansion until final readiness gate
  `PASS`.
- Major WP-018 coach quality expansion beyond narrow evidence/caveat work.
- Recommendation planner implementation before design and data/AI contracts.
- New schema features before migration baseline/schema gate.
- Import cap raise, bulk import scale-up or durable worker implementation
  beyond design.
- Public/friends/shareable workflows.
- Economy, positioning, hard trade, hard clutch, playlist-specific or
  crosshair/spray hard advice.

Evidence: audit `00_EXECUTIVE_SUMMARY.md`, "Do Not Touch Until Fixed Or
Explicitly Scoped"; audit `08_CRITICAL_GAPS.md`; audit matrix AR-026, AR-029,
AR-033, AR-047, AR-049, AR-051, AR-097, AR-098.

## Allowed To Continue

- Foundation-hardening docs, tests, gate, risk and architecture work.
- Narrow WP-018 evidence, caveat, calibration, docs or tests work only when it
  improves readiness, wording, caveats, confidence, metric truth or eval safety
  and does not add unsupported claims.
- Read-only diagnostics and QA reviews.
- Docs-only design work for durable worker/retry ledger.

Evidence: audit `00_EXECUTIVE_SUMMARY.md`, "Continue Feature Development?".

## Requires Foundation-Hardening Before Continuing

- WP-018 planner-like work requires diagnosis registry/planner design,
  source-trust/sample-size policy and semantic evals.
- Any schema-bearing AI metadata change requires migration baseline/schema gate.
- Any larger import behavior requires worker/retry ledger design and later
  explicit implementation WP.
- Any public/friends work requires security/privacy/observability/release gate.

## Revisit After Hardening

- WP-018 remaining slices: resume from the preserved WP-018B context recorded
  by the existing WP-018A diagnosis unless later accepted work changes that,
  then continue category quality, survival/aim/utility/map calibration, weak
  metric suppression, explanation/actionability repair and real usage
  acceptance.
- WP-019 daily UX after foundation gate PASS.
- WP-020 deployment/backup/storage hardening after current foundation blockers
  are resolved or explicitly carried.
- WP-021 personal MVP lock after WP-020 and gate evidence.

## Resume Process

1. Run final readiness review against `04_READINESS_GATE.md`.
2. If PASS, update current status and roadmap docs from restricted lane back to
   the normal WP-018 sequence. Docs-only roadmap edits before this final gate
   do not set `READY_FOR_MAJOR_CS2_FEATURE_WORK` to `YES`.
3. Create a focused WP-018 restart Task Card using the preserved WP-018B
   context unless later accepted work changes the sequence.
4. Keep all carried risks in the risk register with owner/status/target WP.
5. Do not retroactively mark deferred features as implemented.

## Forbidden Additions Before Readiness Gate

- New DB schema features.
- Cap raise above `STEAM_IMPORT_MAX_DEMOS_PER_RUN=1`.
- Live import/parser/evaluator/manual evaluator work without explicit WP.
- New persistent app reports without authorization.
- Public/friends/social/sharing claims.
- Unsupported CS2 hard advice from weak/unavailable metrics.
- Broad route/service/template refactors.

## Roadmap Source Gaps

- `/opt/jc-coach/PROJECT_INDEX.md`: not found. Audit notes
  `docs/project_management/DOCS_INDEX.md` and `DOCS_MAP.md` are the practical
  project index. Evidence: audit `03_DOCS_AND_CONTEXT.md`; audit matrix AR-058.
- `/opt/jc-coach/tasks`: not found. Task specs are under `docs/tasks/`.
  Evidence: audit evidence `docs_inventory.txt`.
- Lowercase requested docs were not found:
  - `docs/current_state.md`
  - `docs/roadmap.md`
  - `docs/known_issues.md`
  Canonical equivalents are `docs/CURRENT_STATUS.md`,
  `docs/project_management/VERSION_ROADMAP.md` and
  `docs/KNOWN_LIMITATIONS.md`.
