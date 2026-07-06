# Agentic Workflow Ops Security

## Agentic Workflow

The repo has a mature written control plane: root contract, source-of-truth order, role cards, invocation modes, output modes, control-plane protection and WP closure rules. The gap is automation: enforcement is mostly manual and should be backed by CI/gate scripts.

## Ops

Backup/restore scripts and restore-on-copy policy exist. Deployment docs and service/nginx config references exist. Observability is not mature: logs are mentioned, but there is no full incident runbook, log taxonomy or operational dashboard.

## Security

Security is acceptable only for controlled personal/VPS use. Auth, owner boundary, CSRF, API auth, strong secret fail-fast and in-memory rate limiting exist. Friends/public exposure remains blocked. Secret handling during this audit was limited to file/variable names only; no secret values were printed.

## Evidence

- `AGENTS.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/SECURITY.md`
- `docs/DEPLOYMENT.md`
- `docs/BACKUP_RESTORE.md`
- `.gitignore`
- `app/main.py`
- `app/services/security.py`
- `scripts/project_gate.py`
