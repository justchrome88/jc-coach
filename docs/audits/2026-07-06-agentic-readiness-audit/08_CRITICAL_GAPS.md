# Critical Gaps

## BLOCKER

1. Migration baseline is missing. Future schema work is unsafe while startup schema mutation remains the compatibility mechanism.
2. Recommendation planner is missing. The coach can track/evaluate goals, but cannot yet choose the primary next recommendation from a verified problem snapshot.

## HIGH

1. No semantic AI evals beyond output schema validation.
2. No CI/pre-commit quality gate for pytest, Ruff, diff checks and project gate.
3. Durable import/Steam worker, retries and job ledger are not production-grade.
4. Source trust and sample-size policy are incomplete across CS2 metrics.
5. Prompt/payload versioning is missing.
6. Data privacy/retention is not ready for friends/public use.
7. Risk register is not structured enough for long-running agentic development.
8. API contract tests are absent.
9. Global DB engine/settings import order remains a safety hazard if tests/scripts are written carelessly.
10. CS2 domain pack lacks accepted economy/positioning/clutch definitions.

## MEDIUM

- Architecture doc is too thin for the current codebase.
- Route/service boundary map is incomplete.
- Old docs are classified but still numerous.
- Observability and incident process are thin.
- Runtime data artifacts in the repo tree require continued discipline.
