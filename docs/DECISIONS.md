# Decisions

Last updated: 2026-07-03.

## Current Decisions

- `docs/PROJECT_CONTROL.md` is the source of truth for project status, priorities and constraints.
- Historical docs are preserved and marked before deletion or archive moves.
- AI provider defaults to `codex_cli_handoff`; local LLM remains optional/scaffolded.
- Steam import uses OpenID + Game Authentication Code + latest share-code cursor + service bot resolver.
- Raw `.dem` deletion is disabled until parsed payload verification exists.
- Friends/public release is blocked by security, ownership, CSRF/rate limit, secrets, backup and observability work.

