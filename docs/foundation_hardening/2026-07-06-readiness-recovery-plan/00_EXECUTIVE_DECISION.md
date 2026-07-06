# Executive Decision

Date: 2026-07-06.

Source audit: `docs/audits/2026-07-06-agentic-readiness-audit`.

## Decision

JC Coach can continue, but only under restricted scope until the foundation
readiness gate passes.

Final project status:

```text
CONTINUE WITH RESTRICTED SCOPE
```

The audit result is not catastrophic: tests passed, Ruff passed, `git diff
--check` passed and the production DB was not mutated. The current readiness
score is still only **66% / 3.30 of 5 across 106 rows**, so the project is not
ready for major coach/domain expansion. Evidence: audit
`00_EXECUTIVE_SUMMARY.md`, "Overall Readiness" and "Continue Feature
Development?".

## Why The Normal CS2 Roadmap Is Restricted

The next normal product lane was `WP-018 Coach Quality Calibration`, followed
by daily UX, deployment/storage hardening and personal MVP lock. Evidence:
`docs/CURRENT_STATUS.md` and `docs/project_management/WP_REGISTRY.md`.

The audit found foundation blockers that can make major CS2 work unsafe or
misleading:

- Schema evolution has no real migration baseline and still depends on startup
  compatibility helpers. Evidence: audit `08_CRITICAL_GAPS.md`, "BLOCKER";
  audit matrix AR-019, AR-026, AR-067.
- The coach can track recommendations but does not yet have a verified problem
  selector or planner. Evidence: audit `08_CRITICAL_GAPS.md`, "BLOCKER"; audit
  matrix AR-033.
- Semantic AI evals, prompt/payload versioning, source trust and sample-size
  policy are missing or incomplete. Evidence: audit
  `05_DATA_METRICS_AI_COACH.md`, "Gaps"; audit matrix AR-038, AR-039, AR-055,
  AR-072, AR-088.
- Quality gates are mostly manual and can be skipped. Evidence: audit
  `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`, "Agentic Workflow"; audit matrix
  AR-009, AR-016, AR-090.

## Frozen Until Readiness Gate

Do not start or continue the following until the readiness gate passes:

- schema features or schema-changing product work;
- import cap raise or larger Steam/demo batch behavior;
- durable worker implementation beyond approved design work;
- public/friends access or sharing features;
- new economy, positioning, clutch, trade or playlist-specific hard coach
  claims;
- broad route/service refactors;
- major CS2 coach/domain expansion after the current accepted recommendation
  loop.

Evidence: audit `00_EXECUTIVE_SUMMARY.md`, "Do Not Touch Until Fixed Or
Explicitly Scoped"; audit `08_CRITICAL_GAPS.md`; audit matrix AR-026, AR-029,
AR-047, AR-049, AR-051, AR-097, AR-098.

## Allowed To Continue

Allowed work is restricted to:

- foundation hardening tasks in this plan;
- docs/source-of-truth cleanup needed for the hardening gate;
- tests/evals/quality gate improvements;
- narrow WP-018 calibration work only when it strengthens evidence, caveats,
  wording, confidence or tests and does not add new unsupported coach claims;
- read-only diagnostics and reviews.

Evidence: audit `00_EXECUTIVE_SUMMARY.md`, "Continue Feature Development?" and
"Shortest Safe Path".

## Why 95%, Not 100%

The target is practical readiness, not theoretical completeness. A 95% gate
means:

- all P0s are closed or explicitly hard-blocked;
- all P1s are closed or have approved workaround and risk acceptance;
- P2/P3 items are triaged as fix now, backlog, accepted risk, duplicate/not
  needed or needs clarification;
- major feature work is blocked by a binary PASS/FAIL gate;
- data, metrics and AI coach logic have contracts, tests or documented gaps.

P2/P3 items such as FACEIT, heatmaps, full E2E coverage, dead-code cleanup,
Playwright, public-readiness observability and broad module refactors can remain
post-readiness backlog if their risks are named and contained. Evidence: audit
`01_AUDIT_MATRIX.md`; audit `09_RECOMMENDED_TASKS.md`.

## Conditions To Resume Major CS2 Development

Major CS2 feature work can resume only when `04_READINESS_GATE.md` evaluates to
PASS.

Minimum conditions:

- migration baseline/schema gate accepted;
- quality gate/CI or mandatory local gate enforced;
- risk register exists with owner/status/target WP/evidence;
- source trust and sample-size policy documented and tested;
- prompt/payload versioning and first semantic AI eval suite accepted;
- diagnosis registry/recommendation planner design accepted, with implementation
  gated before new hard recommendation intelligence;
- security/privacy/public-readiness restrictions remain explicit;
- PM/Execution task lifecycle, reports, checks and docs updates are enforced.

Evidence: audit `10_NEXT_10_TASKS.md`; audit `09_RECOMMENDED_TASKS.md`.

