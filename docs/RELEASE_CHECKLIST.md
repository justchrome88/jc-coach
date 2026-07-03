# Release Checklist

Last updated: 2026-07-03.

## Personal Controlled Use

- `.env` configured.
- Health endpoint responds.
- Login flow works if public route is exposed.
- Core pages load.
- Generated data and secrets are not committed.
- Backups are available before risky operations.

## Friends Alpha Gate

- Stage 1 app-level API auth, CSRF, rate limit, strong secret and Steam OpenID verification checks pass.
- User ownership or enforced single-user mode verified.
- CSRF/same-site protections verified.
- Strong session secret enforced.
- Tests isolated from production settings.
- Backup/restore tested.
- Metrics driving diagnosis have confidence and suppression rules.

## Public Gate

- Friends alpha gate complete.
- Monitoring/observability plan exists.
- Abuse/rate limit behavior verified.
- Data retention policy exists.
- Legal/privacy posture reviewed.
