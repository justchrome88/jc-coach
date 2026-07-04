# Runtime Guardian

## Scope

Protects FastAPI/Jinja runtime behavior, systemd service freshness, deployment smoke and web route safety.

## Activation Paths

- `app/web/*`
- `app/templates/*`
- `app/static/*`
- `app/main.py`
- deployment/systemd/nginx docs or files
- runtime incident reports

## Forbidden Actions

- Restarting production service unless authorized by the task.
- Claiming runtime repair from tests alone when the live service was affected.
- Running live AI/Steam/import/parser jobs as part of page smoke.
- Mutating production DB through login/import/action flows during read-only runtime checks.

## Required Checks

- `systemctl status jc-coach --no-pager` when available.
- Source-level safe tests for touched routes/templates.
- Runtime smoke only when authorized and designed to avoid unintended DB writes.
- `git diff --check`.

## Evidence Required

- Service status before/after if runtime was inspected or restarted.
- Whether service was restarted.
- Runtime smoke URL/status when run.
- Logs or error snippets for incidents.

## Escalation / Blocker Rules

Escalate if a live service restart is required but not authorized, or if authenticated smoke would mutate production DB.

