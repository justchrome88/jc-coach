# Decisions

Last updated: 2026-07-09.

## Current Decisions

- 2026-07-05: `AGENTS.md` is the only root Codex operating contract.
- 2026-07-05: `AGENT.md` is a superseded pointer and must not be used as the active operating contract.
- 2026-07-05: Per-task Hot context is `AGENTS.md`, `docs/CURRENT_STATUS.md` and `docs/project_management/WP_REGISTRY.md`.
- 2026-07-05: New-session Hot context additionally includes `docs/HANDOFF.md`.
- 2026-07-05: Warm docs are read only by task relevance; old reports, prompts, stage reports and generated data reports are evidence/history only.
- 2026-07-05: `docs/project_management/PROJECT_OPERATING_PROTOCOL.md` is the Warm governance protocol, and `docs/project_management/MASTER_WP_CHECKLIST.md` is the Warm/Cold human WP campaign map; neither is per-task Hot context.
- 2026-07-05: `docs/project_management/AGENT_WORKFLOW.md` defines repo-native WP roles and Documentation Steward checks; it is not a runtime agent platform and is not per-task Hot context.
- 2026-07-05: Future prompts should use the Task Card and task type profiles in `docs/project_management/AGENT_WORKFLOW.md` instead of repeating generic workflow instructions.
- 2026-07-06: Agent behavior is controlled through `docs/project_management/AGENT_WORKFLOW.md` plus Warm role cards under `docs/agents/roles/`; new roles require explicit user approval and a role card, with no runtime automation implied.
- 2026-07-06: `v0.9` Real Data Onboarding / Bulk Demo Usage is promoted with warnings by WP-017K for controlled personal use; cap remains `1`, exact playlist mode remains unknown/provenance-only, and friends/public readiness is not claimed.
- 2026-07-06: Future prompts should use invocation modes and output modes from `docs/project_management/AGENT_WORKFLOW.md`; long, reviewable, WP-level, promotion, planning, QA and docs-audit outputs should prefer file-backed reports.
- 2026-07-06: Control-plane docs may be changed only by explicit governance/control-plane tasks; if a rule blocks ordinary work, Codex must stop and request approval instead of weakening the rule.
- 2026-07-08: FH-124R-03 accepted H1 final-readiness rerun evidence, and
  FH-125_128 closes foundation hardening only as
  `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`. The required
  next lane is `POST_FOUNDATION_AUDIT_AND_STABILIZATION`; WP-018, major CS2
  feature work, public/friends access and system `v1.0` claims remain blocked
  until later explicit authorization after audit/stabilization.
- 2026-07-08: `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`. H1 PASS
  evidence, H2 closure and docs-only roadmap edits do not set it to `YES`.
- 2026-07-09: User authorizes
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` after GATE-001. The lane permits
  explicitly scoped WPs for auth / Steam identity, import, demo storage,
  parser, normalized events, derived context, metric snapshots, AI Scout,
  Evidence Validator, missions and coach UI. Preserved guardrails: no
  production DB/schema/data mutation without explicit authorization plus backup
  and pre/post SHA evidence; no live Steam/Valve import without explicit
  authorization; no parser/evaluator/manual evaluator jobs without explicit
  authorization; no raw demo delete/move/compress without explicit storage WP
  scope; no public/friends readiness; no unsupported coach claims; no git push;
  `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` unless a future cap-change WP
  changes it.
- 2026-07-05: `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is out-of-band governance audit evidence and does not consume the planned WP-018 product block.
- 2026-07-05: Match mode classification remains deferred/unknown unless future metadata capture is implemented.
- 2026-07-05: `v0.9` must not claim playlist-specific Premier, Competitive, Wingman, Casual, Deathmatch, FACEIT or custom mode labels.
- 2026-07-05: Steam demo cap remains `1` unless explicitly changed by a future WP.
- Historical: AI provider defaults to `codex_cli_handoff`; local LLM remains optional/scaffolded.
- Historical: Steam import uses OpenID + Game Authentication Code + latest share-code cursor + service bot resolver.
- Historical: Raw `.dem` deletion is disabled until parsed payload verification exists.
- Historical: Friends/public release is blocked by security, ownership, CSRF/rate limit, secrets, backup and observability work.
