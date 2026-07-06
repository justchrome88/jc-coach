# P0/P1 Hardening Backlog

Date: 2026-07-06.

Source audit: `docs/audits/2026-07-06-agentic-readiness-audit`.

This backlog accounts for every P0/P1 row in `01_AUDIT_MATRIX.csv`. Closely
duplicated schema rows are grouped only where they describe the same execution
unit. Every task remains separately executable by Codex Execution.

## P0 Tasks

### FH-P0-001 - Create Migration Baseline And Schema Gate

- Source audit file: `01_AUDIT_MATRIX.csv` AR-019, AR-026, AR-067;
  `08_CRITICAL_GAPS.md`, "BLOCKER"; `09_RECOMMENDED_TASKS.md`,
  TASK-AUDIT-001.
- Severity: P0.
- Layer: Web Application Core / Project Instance.
- Current problem: schema evolution relies on startup create/upgrade behavior
  instead of a migration baseline and diff gate.
- Why it matters: schema feature work can mutate production SQLite state outside
  a controlled migration process.
- Evidence: `docs/MIGRATIONS.md`, `app/db/session.py`, `pyproject.toml`.
- Recommended action: adopt Alembic or equivalent current-schema baseline,
  schema diff policy and production apply approval/SHA policy.
- Acceptance criteria: baseline matches current schema on a copy; production DB
  is untouched; startup helper receives no new schema changes; schema-changing
  WPs require explicit migration scope.
- Required docs updates: `docs/MIGRATIONS.md`, `docs/BACKUP_RESTORE.md`,
  relevant project-management docs if workflow changes.
- Required tests/checks: migration copy/status checks, full pytest, Ruff,
  `git diff --check`, project gate.
- Expected files/areas: migration config/scaffold, `scripts/*`,
  `docs/MIGRATIONS.md`, tests.
- Owner role: DB_GUARDIAN / Execution / QA.
- Dependencies: clean or intentionally accepted worktree; no production DB
  mutation authorization unless separately granted.
- Risk if ignored: future schema work can corrupt or silently drift production.
- Rollback/check strategy: revert migration docs/code/scaffold; verify DB SHA
  unchanged if any DB-dependent command was run.
- Done definition: migration baseline and gate are accepted in a task report
  with checks and production DB safety evidence.

### FH-P0-002 - Keep Public/Friends Access Blocked Until Security Gate

- Source audit file: `01_AUDIT_MATRIX.csv` AR-027; audit
  `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`, "Security"; audit
  `00_EXECUTIVE_SUMMARY.md`, "Do Not Touch Until Fixed Or Explicitly Scoped".
- Severity: P0.
- Layer: Web Application Core / Security.
- Current problem: security is acceptable only for controlled personal/VPS use.
- Why it matters: access expansion would require privacy, observability,
  rate-limit, deployment and owner-boundary guarantees that are not complete.
- Evidence: `docs/SECURITY.md`, `app/main.py`, `tests/test_security.py`,
  `tests/test_ownership.py`.
- Recommended action: add explicit release gate language that blocks
  friends/public work until security/privacy/ops criteria pass.
- Acceptance criteria: public/friends work is visibly blocked in current status,
  roadmap pause/resume and readiness gate; no product access expansion occurs.
- Required docs updates: `docs/CURRENT_STATUS.md`, `docs/KNOWN_LIMITATIONS.md`,
  hardening gate docs.
- Required tests/checks: docs diff check; security tests only if code changes.
- Expected files/areas: docs only unless future security WP is explicitly
  scoped.
- Owner role: Security / PM / QA.
- Dependencies: none.
- Risk if ignored: personal app could be treated as shareable before it is
  safe.
- Rollback/check strategy: revert docs-only restriction changes if replaced by
  stricter gate.
- Done definition: release/access expansion is impossible to claim without a
  PASS gate.

### FH-P0-003 - Design Diagnosis Registry And Recommendation Planner

- Source audit file: `01_AUDIT_MATRIX.csv` AR-033; `08_CRITICAL_GAPS.md`,
  "BLOCKER"; `09_RECOMMENDED_TASKS.md`, TASK-AUDIT-007.
- Severity: P0.
- Layer: AI Coach Product Archetype.
- Current problem: the coach tracks recommendations but does not choose a
  primary recommendation from verified problems.
- Why it matters: major coach quality work needs evidence-backed problem
  selection, not just tracked recommendation progress.
- Evidence: `docs/RECOMMENDATIONS.md`, `docs/KNOWN_LIMITATIONS.md`,
  `app/services/recommendation_tracking.py`.
- Recommended action: design first; implement only under an explicit scoped WP
  after metric/source/eval contracts are ready.
- Acceptance criteria: design names allowed inputs, confidence policy, one
  primary focus rule, weak-metric exclusions and evidence links from problem to
  metric to match to recommendation.
- Required docs updates: `docs/RECOMMENDATIONS.md`, AI coach/domain docs,
  current status after acceptance.
- Required tests/checks: planner tests when implementation starts; for design,
  docs diff check and QA review.
- Expected files/areas: recommendations docs first; later services/tests.
- Owner role: Architect / Metrics Guardian / Execution / QA.
- Dependencies: FH-P1 source trust/sample-size, confidence contract and semantic
  eval baseline.
- Risk if ignored: coach may produce plausible but unsupported next-step advice.
- Rollback/check strategy: revert design/code before it changes accepted
  recommendation behavior.
- Done definition: planner design is accepted and implementation entry criteria
  are explicit.

## P1 Tasks

| ID | Title | Source | Layer | Current problem / why it matters | Recommended action | Acceptance / docs / checks | Owner | Dependencies | Risk if ignored / rollback / done |
|---|---|---|---|---|---|---|---|---|---|
| FH-P1-001 | Expand project gate pre/postflight | AR-009; `06_TESTS_EVALS_QUALITY.md`; `09_RECOMMENDED_TASKS.md` TASK-AUDIT-002 | Agentic Core / Tests | `scripts/project_gate.py` exists but is not a full task preflight/postflight gate; checks can be skipped. | Add explicit gate workflow for status, changed files, required checks and postflight. | Docs: `docs/TESTING.md`, workflow docs if changed. Checks: run gate locally, `git diff --check`. | TEST_GUARDIAN / Execution | none | Ignored: manual gate drift. Rollback: revert script/docs. Done: reports require gate output. |
| FH-P1-002 | Create structured risk register | AR-015; `03_DOCS_AND_CONTEXT.md`; TASK-AUDIT-003 | Agentic Core | Limitations exist but owner/status/target WP/evidence are missing. | Create canonical risk register or extend `KNOWN_LIMITATIONS`. | Acceptance: each risk has criticality, owner, target WP, status, evidence. Checks: docs diff. | PM / Docs | none | Ignored: cross-layer risks lost. Rollback: revert docs. Done: risk register is linked from current docs. |
| FH-P1-003 | Add automated enforcement of agent rules | AR-016; `07_AGENTIC_WORKFLOW_OPS_SECURITY.md` | Agentic Core / CI | No `.github` or pre-commit was found; rules are manual. | Add CI or mandatory local equivalent for pytest/Ruff/diff/project_gate. | Docs: `docs/TESTING.md`, `AGENT_WORKFLOW.md`. Checks: gate passes locally. | TEST_GUARDIAN / QA | FH-P1-001 | Ignored: completion claims can bypass checks. Rollback: remove CI/gate. Done: failure blocks PASS claims. |
| FH-P1-004 | Expand architecture map | AR-017; `04_ARCHITECTURE_CODEBASE.md` | Web Core | `docs/ARCHITECTURE.md` is thin for current route/service/data surface. | Add module, data-flow and mutation-boundary map. | Docs: architecture. Checks: docs diff; targeted tests if code touched. | Architect / Runtime | none | Ignored: agents mutate wrong layer. Rollback docs. Done: boundaries are inspectable. |
| FH-P1-005 | Add API contract inventory/tests | AR-018; TASK-AUDIT-008 | Web Core | API contracts are not versioned or tested as contracts. | Inventory core endpoints and add smoke/contract tests for critical read/mutation routes. | Docs: API section. Checks: contract/web tests, full tests if routes touched. | Runtime / QA | FH-P1-004 | Ignored: endpoint drift. Rollback tests/docs. Done: core contracts are tested. |
| FH-P1-006 | Harden owner/auth edge state | AR-020; `07_AGENTIC_WORKFLOW_OPS_SECURITY.md` | Web Core / Security | Owner model is good but multi-record/config edge cases need explicit handling. | Add explicit owner state/config docs and tests or accepted limitation. | Docs: security/current limitations. Checks: auth/security/ownership tests. | Security / Runtime | none | Ignored: single-owner assumption stays fragile. Rollback scoped changes. Done: edge cases are tested or accepted risk. |
| FH-P1-007 | Create job error taxonomy and result_json schema | AR-022; AR-029; TASK-AUDIT-010 | Web Core / Import | Job status is coarse; result_json is canonical but not fully contracted. | Document outcome taxonomy and result_json schema. | Docs: Steam/import architecture. Checks: docs diff; importer tests if code touched. | Import Guardian | none | Ignored: ambiguous import failures. Rollback docs. Done: outcomes have schema and examples. |
| FH-P1-008 | Create safe env reference | AR-025 | Web Core / Ops | Required/optional env vars are not fully documented in a safe reference. | Document env variable names and purpose without values. | Docs: env/security/deployment. Checks: docs diff; no secret values. | Security / Docs | none | Ignored: unsafe env handling. Rollback docs. Done: reference exists and reveals no values. |
| FH-P1-009 | Plan durable worker/retry ledger before cap raise | AR-029; TASK-AUDIT-010 | Web Core / Ops | BackgroundTasks are fragile for larger Steam/import behavior. | Design worker, retry ledger and staged DB requirements; do not implement cap raise. | Docs: import architecture. Checks: docs diff. | Import / Architect | FH-P1-007, FH-P0-001 for later implementation | Ignored: cap raises unsafe. Rollback design docs. Done: cap raise blocked until design accepted. |
| FH-P1-010 | Create generic AI coach archetype model doc | AR-031 | AI Coach | Coach archetype is not separated from CS2 domain pack. | Define coach-core concepts independent of CS2 domain. | Docs: AI coach/recommendations. Checks: docs diff. | Architect / Metrics | none | Ignored: domain and coach logic stay tangled. Rollback docs. Done: separation is documented. |
| FH-P1-011 | Enforce one primary accepted focus until planner exists | AR-032 | AI Coach | Multiple goals could be misread as accepted hard focus. | Document and enforce one primary accepted focus until planner passes. | Docs: recommendations/current status. Checks: recommendation tests if code touched. | Metrics / PM | FH-P0-003 | Ignored: conflicting advice. Rollback docs/code. Done: one-focus rule explicit. |
| FH-P1-012 | Calibrate progress wording and sample confidence | AR-034 | AI Coach | Progress wording can overstate small-sample evidence. | Calibrate wording/caveats for current recommendation progress. | Docs/tests: recommendation tracking and UI if changed. | Metrics / UI / QA | source trust policy | Ignored: overconfident user guidance. Rollback scoped copy/tests. Done: wording matches confidence. |
| FH-P1-013 | Keep metric_confidence mandatory | AR-035 | AI Coach / Metrics | Evaluations rely on confidence and must not regress. | Add contract/check that evaluations include `metric_confidence`. | Docs: recommendations/metrics. Checks: recommendation tests. | Metrics / QA | none | Ignored: weak evidence becomes hard result. Rollback tests/code. Done: missing confidence fails. |
| FH-P1-014 | Create coach advice confidence contract | AR-036 | AI Coach / Metrics | Metric confidence exists; advice-level confidence contract is missing. | Define advice confidence from source, sample, metric reliability and caveats. | Docs: AI coach/METRICS. Checks: confidence tests if code touched. | Metrics / Architect | FH-P1-020 | Ignored: advice overclaims. Rollback docs/code. Done: advice confidence is defined. |
| FH-P1-015 | Add evidence link model | AR-037 | AI Coach | Problem-to-recommendation explainability is incomplete. | Define evidence chain from problem -> metric -> match -> recommendation. | Docs/tests as needed. | Metrics / Architect | FH-P1-014 | Ignored: unverifiable recommendations. Rollback docs/code. Done: chain is required for hard advice. |
| FH-P1-016 | Add prompt/payload versioning | AR-038; TASK-AUDIT-005 | AI Coach | AI prompt and payload versions are missing. | Add `prompt_version` and `payload_version` to metadata/persistence or document first if code not scoped. | Docs: `AI_COACH.md`. Checks: AI coach/validator tests if code touched. | Metrics / Execution / QA | FH-P0-001 if schema change is needed | Ignored: AI outputs not reproducible. Rollback before production report generation. Done: versions visible in result metadata. |
| FH-P1-017 | Build semantic AI eval suite | AR-039, AR-088; TASK-AUDIT-006 | AI Coach / Tests | Validator checks schema but not advice entailment/quality. | Add first golden eval fixtures for supported/unsupported claims. | Docs: testing/AI. Checks: eval tests plus existing AI tests. | QA / Metrics | FH-P1-014 | Ignored: schema-valid bad advice. Rollback eval fixtures/tests. Done: eval suite blocks overclaim cases. |
| FH-P1-018 | Add CS2 match/round domain map | AR-043; TASK-AUDIT-009 | CS2 Domain | Domain facts are scattered. | Document match/round/sides/map/source facts and limits. | Docs: CS2 domain pack. Checks: docs diff. | Docs / Metrics | none | Ignored: agents infer unsupported facts. Rollback docs. Done: domain map exists. |
| FH-P1-019 | Keep side metrics display-only until confidence improves | AR-045 | CS2 Domain / Metrics | CT/T side metrics are not ready for hard advice. | Document display-only status and parser confidence requirement. | Docs: metrics/domain. Checks if code touched. | Metrics | FH-P1-020 | Ignored: side-based overclaims. Rollback. Done: side hard advice is blocked. |
| FH-P1-020 | Block hard trade recommendations before parser hardening | AR-047 | CS2 Domain / Metrics | Trade logic is weak for hard recommendations. | Explicitly block hard trade claims until parser evidence improves. | Docs: metrics/domain/recommendations. | Metrics | none | Ignored: unsupported trade coaching. Rollback docs. Done: hard trade claims forbidden. |
| FH-P1-021 | Keep source limitations visible | AR-054 | CS2 Domain | Demo/Steam/FACEIT/source limits must remain visible in coach output. | Add source limitation contract for UI/coach output. | Docs/tests if UI/code touched. | Metrics / UI | FH-P1-023 | Ignored: source overtrust. Rollback. Done: source limits visible. |
| FH-P1-022 | Define sample-size thresholds per metric/category | AR-055; TASK-AUDIT-004 | CS2 Domain / Metrics | Sample-size policy is incomplete. | Define thresholds and caveats per metric/category. | Docs: `METRICS.md`; checks: confidence/golden fixture tests. | Metrics / QA | FH-P1-023 | Ignored: small-sample overconfidence. Rollback rules/tests. Done: thresholds are enforced or documented. |
| FH-P1-023 | Keep formula/reliability sync tests | AR-068 | Data / Metrics | Formula docs and code must stay synchronized. | Maintain/extend sync tests for accepted metrics. | Docs/tests: metric truth. | Metrics / QA | none | Ignored: docs/code drift. Rollback tests/docs. Done: sync check passes. |
| FH-P1-024 | Add golden aggregate fixture suite | AR-069, AR-087 | Data / Metrics / Tests | Broader aggregate fixtures are incomplete. | Add fixtures for accepted core metrics. | Checks: metric truth/analytics/parser confidence tests. | Metrics / QA | FH-P1-022 | Ignored: aggregate regressions. Rollback fixtures/tests. Done: core accepted metrics have golden fixtures. |
| FH-P1-025 | Create source trust registry | AR-072; TASK-AUDIT-004 | Data / Metrics | Source trust levels for CSV/JSON/demo/Steam/FACEIT are incomplete. | Define trust levels and usage rules. | Docs: metrics/import/current limitations. Checks if code touched. | Metrics / Import | none | Ignored: weak sources drive hard advice. Rollback docs/code. Done: source trust is referenced by coach policy. |
| FH-P1-026 | Document aggregation rules | AR-073 | Data / Metrics | Aggregation semantics are not fully documented. | Document rules and add representative fixtures. | Docs/tests: analytics/metrics. | Metrics / QA | FH-P1-024 | Ignored: inconsistent comparisons. Rollback. Done: aggregation cases are tested. |
| FH-P1-027 | Version metric registry/prompt payload snapshots | AR-076 | Data / AI Reproducibility | Calculation and prompt inputs are not fully reproducible across changes. | Version metric registry and payload snapshots. | Docs/tests: AI/metrics. | Metrics / Architect | FH-P1-016 | Ignored: old AI outputs cannot be reproduced. Rollback. Done: versioned snapshots exist. |
| FH-P1-028 | Add global DB import-order smoke guard | AR-081 | Runtime / DB | Global engine/settings import order can be unsafe outside pytest discipline. | Reduce global binding or add import-order smoke tests. | Checks: config/db tests, full pytest. | DB / Runtime / QA | FH-P0-001 | Ignored: careless scripts can hit prod DB. Rollback tests/code. Done: unsafe import order is guarded. |
| FH-P1-029 | Add CI quality gates | AR-090 | Tests / CI | No CI workflow found. | Add CI or accepted mandatory local substitute. | Checks: CI config validates or local gate passes. | TEST_GUARDIAN | FH-P1-003 | Ignored: regressions land unchecked. Rollback CI. Done: required checks are standard. |
| FH-P1-030 | Keep SHA in every DB-impacting WP | AR-093 | Ops / DB | Backup/SHA discipline exists and must remain mandatory. | Include DB SHA requirement in gate/report template. | Docs: workflow/testing/backup. | DB / PM | FH-P1-001 | Ignored: DB impact unclear. Rollback docs. Done: report template requires SHA for DB-impacting WPs. |
| FH-P1-031 | Add secret redaction command policy | AR-095 | Security | Secret handling is good but command policy should be explicit. | Document allowed commands: names only, no values. | Docs: security/gate. Checks: docs diff. | Security | none | Ignored: secret leakage risk. Rollback docs. Done: reports forbid secret values. |
| FH-P1-032 | Keep public-readiness rate-limit restriction | AR-097 | Security | In-memory rate limiting is not public-grade. | Document no public readiness; later reverse-proxy/Redis limiter. | Docs only until public WP. | Security / Runtime | FH-P0-002 | Ignored: false public readiness. Rollback docs. Done: public claims blocked. |
| FH-P1-033 | Add data privacy/retention policy before sharing | AR-098 | Security / Privacy | Privacy/retention is not ready for friends/public use. | Define policy before any sharing/social feature. | Docs: security/demo storage/limitations. | Security / PM | FH-P0-002 | Ignored: sensitive data exposure. Rollback docs. Done: sharing blocked pending policy. |

## P1 Rows Accounted As Constraints In Other Tasks

- AR-032 is implemented as FH-P1-011.
- AR-035 is implemented as FH-P1-013.
- AR-045 is implemented as FH-P1-019.
- AR-047 is implemented as FH-P1-020.
- AR-054 is implemented as FH-P1-021.
- AR-068 is implemented as FH-P1-023.
- AR-093 is implemented as FH-P1-030.
- AR-095 is implemented as FH-P1-031.
- AR-097 is implemented as FH-P1-032.
- AR-098 is implemented as FH-P1-033.

