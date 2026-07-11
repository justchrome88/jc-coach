# UI Coach Guardian

## Scope

Protects `/coach` UI honesty, read-only page rendering, current recommendation labeling and runtime smoke expectations.

## Activation Paths

- `app/web/*coach*`
- `app/templates/*coach*`
- `app/static/*coach*`
- `/coach` route/template tests
- coach UI docs/audit files

## Forbidden Actions

- Claiming current recommendation is a verified top problem unless planner evidence exists.
- Creating recommendations/evaluations/reports from GET `/coach`.
- Starting AI/Steam/import/parser jobs from page render.
- Broad UI redesign outside the authorized coach loop.

## Required Checks

- Coach UI targeted tests when `/coach` changes.
- Recommendation read/write no-mutation tests when route behavior changes.
- Runtime freshness smoke after deployment/restart when authorized.
- `git diff --check`.

## Evidence Required

- GET `/coach` read-only evidence.
- Labels for weak metrics and AI validation/fallback status.
- Whether service restart/smoke was run.
- Tests run and result.

## Escalation / Blocker Rules

Block if a requested UI change would hide confidence warnings, introduce hidden writes, or imply planner behavior that does not exist.

