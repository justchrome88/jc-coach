# Recommended Tasks

## TASK-AUDIT-001: Create Migration Baseline And Schema Gate

- Priority: P0
- Criticality: BLOCKER
- Layer: Web Application Core / Project Instance
- Problem: Schema evolution relies on legacy startup helpers instead of a migration baseline.
- Evidence: `docs/MIGRATIONS.md`, `app/db/session.py`, `pyproject.toml`.
- Why it matters: Future schema changes can mutate production DB outside a controlled migration process.
- Desired outcome: Alembic or equivalent baseline matching current production schema, with copy-check and SHA policy.
- Acceptance criteria: Baseline exists; production apply requires explicit approval; startup helper receives no new schema changes; tests pass.
- Files likely involved: `pyproject.toml`, migration config, `docs/MIGRATIONS.md`, `scripts/*`, tests.
- Tests required: migration status/copy tests, full pytest, Ruff, diff check.
- Docs required: update migration and backup docs.
- Risk: High; must not mutate production DB.
- Rollback: Revert migration scaffolding docs/code; production DB untouched.
- Suggested agent: DB_GUARDIAN

## TASK-AUDIT-002: Add CI Or Mandatory Quality Gate

- Priority: P1
- Criticality: HIGH
- Layer: Agentic Development Core / Tests
- Problem: Quality gates are documented but not automatically enforced.
- Evidence: `scripts/project_gate.py`, `docs/TESTING.md`, `NOT_FOUND:.github/workflows`.
- Why it matters: Agentic development depends on repeatable gates.
- Desired outcome: CI or a mandatory local gate command for pytest, Ruff, diff check and project_gate.
- Acceptance criteria: Gate command documented; CI or equivalent configured; failure blocks completion claims.
- Files likely involved: `.github/workflows/*` or scripts/docs.
- Tests required: Run gate locally.
- Docs required: `docs/TESTING.md`, `AGENT_WORKFLOW.md` if workflow changes.
- Risk: Low/medium.
- Rollback: Remove CI/gate changes.
- Suggested agent: TEST_GUARDIAN

## TASK-AUDIT-003: Create Structured Risk Register

- Priority: P1
- Criticality: HIGH
- Layer: Agentic Development Core
- Problem: Limitations are listed but not managed with owner/status/target WP.
- Evidence: `docs/KNOWN_LIMITATIONS.md`, `docs/CURRENT_STATUS.md`.
- Why it matters: Long-running agentic work needs durable risk ownership.
- Desired outcome: Canonical risk register or enriched limitations doc.
- Acceptance criteria: Each risk has criticality, owner, target WP, status and evidence.
- Files likely involved: `docs/KNOWN_LIMITATIONS.md` or a canonical risk doc plus docs index/map.
- Tests required: docs-only diff check.
- Docs required: DOCS_INDEX/DOCS_MAP if new doc.
- Risk: Low.
- Rollback: Revert docs.
- Suggested agent: PM_ORCHESTRATOR

## TASK-AUDIT-004: Define Source Trust And Sample-Size Policy

- Priority: P1
- Criticality: HIGH
- Layer: AI Coach Archetype / CS2 Domain Pack
- Problem: Metric reliability exists, but source trust and sample-size thresholds are not unified.
- Evidence: `docs/METRICS.md`, `app/services/metric_confidence.py`, `docs/CURRENT_STATUS.md`.
- Why it matters: Coach advice can become overconfident on weak/small samples.
- Desired outcome: Source trust registry and sample-size rules per metric/category.
- Acceptance criteria: CSV/JSON/demo/Steam/FACEIT states defined; thresholds documented; tests cover representative cases.
- Files likely involved: `docs/METRICS.md`, `app/services/metric_confidence.py`, tests.
- Tests required: metric confidence tests and golden fixtures.
- Docs required: `docs/METRICS.md`, possibly `docs/RECOMMENDATIONS.md`.
- Risk: Medium.
- Rollback: Revert rules/tests.
- Suggested agent: METRICS_GUARDIAN

## TASK-AUDIT-005: Add Prompt/Payload Versioning

- Priority: P1
- Criticality: HIGH
- Layer: AI Coach Archetype
- Problem: AI prompt and payload versions are explicitly missing.
- Evidence: `docs/AI_COACH.md`, `app/services/ai_coach.py`.
- Why it matters: AI outputs are not reproducible across prompt changes.
- Desired outcome: Version fields in AI payload/handoff/result metadata.
- Acceptance criteria: Payload includes prompt_version/payload_version; result persistence stores them; tests updated.
- Files likely involved: `app/services/ai_coach.py`, tests, `docs/AI_COACH.md`.
- Tests required: AI coach tests, AI validator tests.
- Docs required: `docs/AI_COACH.md`.
- Risk: Medium.
- Rollback: Revert fields/tests before production report generation.
- Suggested agent: METRICS_GUARDIAN

## TASK-AUDIT-006: Build First Semantic AI Eval Suite

- Priority: P1
- Criticality: HIGH
- Layer: AI Coach Archetype / Tests
- Problem: Validator checks schema/metric IDs but not advice entailment or quality.
- Evidence: `tests/test_ai_validator.py`, `NOT_FOUND:evals`.
- Why it matters: Schema-valid advice can still be wrong or too strong.
- Desired outcome: Small golden eval set for supported/unsupported coach claims.
- Acceptance criteria: At least 10 fixtures covering correct caveats, hallucinated metrics, overconfident weak claims and safe fallback.
- Files likely involved: `tests/`, possible `evals/`, `docs/AI_COACH.md`.
- Tests required: new eval tests plus existing AI tests.
- Docs required: testing/AI docs.
- Risk: Low/medium.
- Rollback: Revert eval fixtures/tests.
- Suggested agent: QA_REVIEWER

## TASK-AUDIT-007: Design Diagnosis Registry And Recommendation Planner

- Priority: P0
- Criticality: BLOCKER
- Layer: AI Coach Archetype
- Problem: The coach tracks recommendations but does not choose a primary recommendation from verified problems.
- Evidence: `docs/RECOMMENDATIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `app/services/recommendation_tracking.py`.
- Why it matters: Coach quality cannot improve safely without verified problem selection.
- Desired outcome: Design then implement diagnosis registry/top problem planner under WP-018 scope.
- Acceptance criteria: Planner uses only allowed metrics; produces one primary focus with evidence/confidence; tests prove weak metrics cannot drive hard recommendations.
- Files likely involved: `docs/RECOMMENDATIONS.md`, `app/services/*`, tests.
- Tests required: metric truth, recommendation tracking, planner tests, AI validator tests.
- Docs required: recommendations and current status after acceptance.
- Risk: High; avoid changing production DB without explicit scope.
- Rollback: Revert planner code/docs; keep existing #5 untouched unless scoped.
- Suggested agent: METRICS_GUARDIAN

## TASK-AUDIT-008: Expand Architecture Map And API Contracts

- Priority: P2
- Criticality: MEDIUM
- Layer: Web Application Core
- Problem: Architecture and endpoint contract docs are too thin for the current app surface.
- Evidence: `docs/ARCHITECTURE.md`, `README.md`, `app/api/routes.py`, `app/web/routes.py`.
- Why it matters: Agents need clear mutation/read boundaries.
- Desired outcome: Module map, route inventory, mutation matrix and API contract tests for critical routes.
- Acceptance criteria: Docs list route/service/data boundaries; tests cover core contracts.
- Files likely involved: docs, tests.
- Tests required: contract/web smoke tests.
- Docs required: architecture/API section.
- Risk: Low.
- Rollback: Revert docs/tests.
- Suggested agent: RUNTIME_GUARDIAN

## TASK-AUDIT-009: Add CS2 Domain Pack Document

- Priority: P2
- Criticality: MEDIUM
- Layer: CS2 Domain Pack
- Problem: CS2 domain rules are scattered across metrics/import/parser docs.
- Evidence: `docs/METRICS.md`, `docs/STEAM_IMPORT.md`, `docs/KNOWN_LIMITATIONS.md`.
- Why it matters: Agents may infer unsupported CS2 facts.
- Desired outcome: Canonical CS2 domain pack with maps, modes, rounds, sides, utility, trades, economy unavailable status and glossary.
- Acceptance criteria: Domain facts classified as trusted/weak/unavailable; docs index/map updated.
- Files likely involved: new or existing domain doc, DOCS_INDEX, DOCS_MAP.
- Tests required: docs diff check; no runtime tests unless code changes.
- Docs required: CS2 domain pack and navigation.
- Risk: Low.
- Rollback: Revert docs.
- Suggested agent: DOCUMENTATION_STEWARD

## TASK-AUDIT-010: Plan Durable Import Worker And Retry Ledger

- Priority: P1
- Criticality: HIGH
- Layer: Web Application Core / Ops
- Problem: Steam/import uses BackgroundTasks and coarse job status; docs identify alpha limitations.
- Evidence: `app/api/routes.py`, `app/web/routes.py`, `app/db/models.py`, `docs/KNOWN_LIMITATIONS.md`.
- Why it matters: Cap raises or larger onboarding are unsafe without durable job truth.
- Desired outcome: Design and staged implementation plan for worker, retry ledger and result_json schema.
- Acceptance criteria: No cap raise; design accepted; future implementation tasks scoped with DB/backup requirements.
- Files likely involved: docs first, later import services/models.
- Tests required: none for design; later mocked worker tests.
- Docs required: Steam/import architecture docs.
- Risk: High if implemented prematurely.
- Rollback: Revert docs/design.
- Suggested agent: IMPORT_GUARDIAN
