# Changelog

This file is reserved for curated release notes.

For chronological engineering detail, see `WORKLOG.md`.

## 2026-07-03

- Added Stage 7 Steam cursor truth: explicit cursor source/advance/outcome semantics, `knowncode=0` initial-sentinel handling and mocked cursor tests without live Steam jobs.
- Added Stage 6 parser fact confidence hardening: early deaths no longer silently fall back to entry deaths, parser warnings are clearer, and parser confidence tests were added.
- Added Stage 5 Metric Truth Layer: runtime metric registry, reliability/usage policy, tests, AI payload metadata and recommendation hard-signal suppression for weak metrics.
- Added Stage 4 recommendation read/write split: GET/read helpers no longer create recommendations or evaluations, while POST actions remain explicit mutations.
- Added Stage 3 migration discipline scaffold: schema inventory, migration policy, copy-check scripts and migration safety tests.
- Added Stage 2 ownership hardening: first credentialed owner policy, blocked second self-registration, owner-only session boundary and Steam OpenID callback owner linking.
- Added Stage 1 Security P0 hardening: protected API, CSRF checks, MVP rate limits, strong secret fail-fast and Steam OpenID assertion verification.
- Added Hardening Stage 0 safety foundation: backup/restore scripts, test DB isolation guard and safe testing docs.
- Consolidated documentation under `docs/PROJECT_CONTROL.md`.
- Added canonical current-status, milestone, roadmap and domain docs.
- Added documentation audit, conflict and deprecation tracking files.
