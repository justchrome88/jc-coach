# Changelog

This file is reserved for curated release notes.

For chronological engineering detail, see `WORKLOG.md`.

## 2026-07-03

- Added Stage 3 migration discipline scaffold: schema inventory, migration policy, copy-check scripts and migration safety tests.
- Added Stage 2 ownership hardening: first credentialed owner policy, blocked second self-registration, owner-only session boundary and Steam OpenID callback owner linking.
- Added Stage 1 Security P0 hardening: protected API, CSRF checks, MVP rate limits, strong secret fail-fast and Steam OpenID assertion verification.
- Added Hardening Stage 0 safety foundation: backup/restore scripts, test DB isolation guard and safe testing docs.
- Consolidated documentation under `docs/PROJECT_CONTROL.md`.
- Added canonical current-status, milestone, roadmap and domain docs.
- Added documentation audit, conflict and deprecation tracking files.
