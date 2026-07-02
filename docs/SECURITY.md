# Security

Last updated: 2026-07-03.

## Current Truth

The app is acceptable only for personal/VPS use under controlled access. Login/register and nginx deployment scaffolding exist, but the product is not ready for friends/public exposure.

## Blockers For Friends/Public Use

- Non-health `/api/*` endpoints need auth or explicit API token policy.
- Sensitive records need user ownership or declared/enforced single-user mode.
- State-changing actions need CSRF or equivalent same-site hardening.
- Strong `SESSION_SECRET_KEY` must be enforced outside local development.
- Tests must be isolated from production DB/settings.
- Backup/restore and operational visibility need to be documented and verified.

## Steam Secret Rules

- Do not ask for or store a user's Steam password, Steam Guard approval, refresh token or personal credentials.
- Service bot credentials belong only to a dedicated bot account and must not be committed.
- `.env`, bot credentials and tokens stay out of git.

