# FH-045/FH-046 Endpoint Classes And Route Validation Inventory Batch Report

Date: 2026-07-07

Task card:
`/opt/jc-coach-pm/outbox/2026-07-07_FH-046_batch_FH-045_046_task-card.md`

Context manifest:
`/opt/jc-coach-pm/indexes/current_context_manifest.json`

## Result

- FH-045 verdict: `PASS`
- FH-046 verdict: `PASS_WITH_WARNINGS`
- Batch verdict: `PASS_WITH_WARNINGS`

FH-045 passed: current endpoint groups are now classified in
`docs/API_CONTRACTS.md` and `docs/ARCHITECTURE.md` as read-only,
write/mutation, import/parser/evaluator-risk, auth/owner-sensitive,
DB/schema-risk or unknown, with future review/check expectations.

FH-046 passed with warnings: route-level validation and ownership/auth checks
are inventoried at a practical level from `app/main.py`, `app/api/routes.py`,
`app/web/routes.py` and `app/services/security.py`. Missing or implicit
validation is marked as follow-up candidate work rather than accepted complete
coverage.

Warning: the supplied context manifest task metadata still named prior accepted
task `FH-042_043`; the explicit task card named this batch as `FH-045_046` and
was treated as controlling under the source-of-truth order.

## Evidence

- Initial `git status --short`: clean.
- Read Hot/new-session context:
  - `AGENTS.md`
  - `docs/CURRENT_STATUS.md`
  - `docs/project_management/WP_REGISTRY.md`
  - `docs/HANDOFF.md`
- Read explicit task inputs:
  - task card listed above
  - context manifest listed above
- Targeted route evidence read:
  - `app/main.py` middleware/public-path/auth/CSRF boundary
  - `app/api/routes.py` API endpoint declarations, HTTP exception handling and
    route-owned validation
  - `app/web/routes.py` web endpoint declarations, redirects, form handling and
    service exception handling
  - `app/services/security.py` CSRF, API token and rate-limit helper behavior
- Required checks run before final report:
  - `.venv/bin/python scripts/project_gate.py preflight` passed.
  - `.venv/bin/python scripts/project_gate.py changed` passed before and after
    report creation and activated `DOCUMENTATION_STEWARD` and
    `PM_ORCHESTRATOR`.
  - `.venv/bin/python scripts/project_gate.py required-checks` passed.
  - `git diff --check` passed.
  - `.venv/bin/python scripts/project_gate.py postflight` passed.
- Final changed/untracked files:
  - `M docs/API_CONTRACTS.md`
  - `M docs/ARCHITECTURE.md`
  - `?? docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-045_046_endpoint-classes-route-validation-inventory-batch_report.md`
- Documentation Steward checklist:
  - Report docs update checklist completed for the scoped API/architecture
    inventory.
  - Hot/current status docs update not required; task did not change project
    status, roadmap state or active WP state.
  - Navigation docs update not required; the task updated existing canonical
    route docs and wrote the task-card-specified report only.
  - Changed docs do not weaken `AGENTS.md` or control-plane policy.

## Files Changed

- `docs/API_CONTRACTS.md`
  - Added endpoint safety classes.
  - Added route-level validation inventory and conservative validation gaps.
- `docs/ARCHITECTURE.md`
  - Added validation responsibility classes.
  - Added endpoint safety classes and review/check expectations.
  - Added route-level validation inventory by route area.
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-045_046_endpoint-classes-route-validation-inventory-batch_report.md`
  - Added this Executor report.

## Safety Declarations

- Docs-only task.
- No code, tests, scripts, runtime config, service/deploy config, package state
  or generated app reports changed.
- No production DB mutation.
- No production DB content inspection was performed. The required preflight
  gate reported the current production DB SHA as
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- No live Steam/Valve import run.
- No parser jobs run.
- No evaluator or manual evaluator jobs run.
- No service start/restart.
- No `git add`, commit or push.
- No validation behavior, auth/owner checks, route handlers, schemas, services,
  DB models or startup behavior changed.

## FH-045 Detail

Endpoint classes documented:

- `read-only`
- `write/mutation`
- `import/parser/evaluator-risk`
- `auth/owner-sensitive`
- `DB/schema-risk`
- `unknown`

The docs now state which classes require focused tests, DB/SHA evidence when
production DB inspection/mutation is involved, import/parser/evaluator
authorization, or stronger PM review.

## FH-046 Detail

Validation inventory documented:

- middleware-owned auth/API-token/CSRF/rate-limit/public-path checks
- framework-owned FastAPI/Starlette type and request binding
- route-owned validation and exception translation
- service-owned validation surfaced through route responses
- implicit/follow-up gaps for filters, enums, free text, extension counts,
  web error conventions, API-token write coverage and import/storage safety

Conservative follow-up candidates were documented without implementing fixes.

## Discovery Result

```yaml
discovery_result:
  completeness_estimate: "Practical route inventory complete for current core app/main.py, app/api/routes.py and app/web/routes.py surface; deeper service-level validation matrix remains future work."
  missing_items_found: true
  followup_required: true
  followup_tasks_recommended:
    - proposed_id: "FH-047"
      title: "Route validation and auth boundary test matrix"
      reason: "Validation gaps are now inventoried; focused tests should lock API-token/session CSRF behavior, route-owned validation, service exception translation and implicit web/API edge cases."
      risk: "P1"
      suggested_scope: "tests"
      needs_user_decision: false
    - proposed_id: "FH-044"
      title: "Endpoint safety rules for future checks"
      reason: "Endpoint classes now identify which routes require DB/SHA declarations, import/parser/evaluator authorization and stronger PM review before mutation-risk checks."
      risk: "P1"
      suggested_scope: "docs-only"
      needs_user_decision: false
```

## Blockers

None.

## Next WP

Proceed to PM review. Expected follow-up work is FH-044/FH-047-style rule/test
work based on the documented endpoint classes and validation gaps.
