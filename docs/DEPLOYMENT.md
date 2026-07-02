# Deployment

Last updated: 2026-07-03.

## Current Shape

The repository includes deployment references:

- `deploy/systemd/jc-coach.service`
- `deploy/nginx/jcnodex.conf`
- `docs/PUBLIC_DEPLOYMENT_CHECKLIST.md`

The current deployment is suitable for controlled personal/VPS use only.

## Public/Friends Gate

Do not claim friends/public readiness until `docs/SECURITY.md` blockers are closed and verified.

## Operational Notes

- Keep secrets in environment/config, not git.
- Keep generated data under `data/` out of git.
- Verify health, auth flow and core pages after deployment changes.

