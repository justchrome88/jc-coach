# Current Status

Last updated: 2026-07-07.

## Snapshot

- Product version: `v0.9`.
- Current lane: Foundation Hardening / Readiness Recovery after the
  2026-07-06 agentic-readiness audit.
- Current active WP: none; latest completed product WP is `WP-017K Real Data
  Onboarding Promotion to v0.9`.
- Next unrestricted product WP: `WP-018 Coach Quality Calibration`, paused
  pending final readiness gate `PASS`.
- Allowed interim WP-018 work is limited to narrow evidence, caveat,
  calibration, docs or tests work that improves readiness and does not add
  unsupported coach/domain claims.
- Promotion status: `v0.9` is promoted with warnings by WP-017K. Warnings and limitations must carry forward into WP-018.
- Latest known production DB SHA: `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33` from WP-017H evidence and the 2026-07-06 agentic-readiness audit. Re-check before any WP that depends on current DB state.

## Foundation Hardening Status

- 2026-07-06 read-only agentic-readiness audit result: `66%` readiness
  (`3.30/5` across 106 audit rows).
- Audit decision: `YES, BUT` - continue only small/scoped work while fixing
  foundation P0/P1 items before major coach/domain expansion.
- Recovery plan:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/`.
- Foundation risk register:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`.
- Current project status for execution planning:
  `CONTINUE WITH RESTRICTED SCOPE`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK`: `NO` until the readiness gate in the
  recovery plan passes.
- Docs-only roadmap edits cannot set `READY_FOR_MAJOR_CS2_FEATURE_WORK` to
  `YES`; only final readiness gate `PASS` can authorize that status change.
- After gate `PASS`, an appropriate follow-up task must update current
  status/roadmap docs and create a focused WP-018 restart task card. The
  preserved resume context is the canonical WP-018 sequence beginning from the
  WP-018B context recorded by the existing WP-018A diagnosis, unless later
  accepted work changes that.

## Runtime Basics

- Project path: `/opt/jc-coach`.
- Service: `jc-coach.service`.
- Backend: Python / FastAPI / Uvicorn.
- Bind target: `127.0.0.1:8010`.
- Production DB: `data/cs2_coach.db`.
- Shell service calls that touch Steam/import temp storage must use `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp` and `TMP=/opt/jc-coach/data/tmp` when explicitly authorized.

## Accepted State

- `v0.8` is accepted for controlled personal Recommendation Loop Acceptance.
- Active accepted recommendation for hard progress is survival recommendation `#5`.
- Recommendation `#5` has three real evaluations with `metric_confidence` and progress `3/10` after matches `#72`, `#75` and `#76`.
- Real data onboarding evidence after WP-017G/H: about 76 total matches, 22 playable demo matches, 20 exact playable dates and parser artifacts for 22 playable demos.
- Controlled Steam/Valve import can process one-demo capped personal batches with warnings; cap remains `1`.
- Root `AGENTS.md` and canonical `docs/project_management/WP_REGISTRY.md` exist.
- WP-017J accepted exact playlist-mode deferral for `v0.9`.
- WP-017U added a practical project operating protocol and master WP checklist
  as Warm governance/planning references.
- WP-017V added a repo-native agent workflow and Documentation Steward / Docs
  Currency Agent as Warm governance/process references.
- WP-017W added task type profiles, role invocation shortcuts and a short Task
  Card prompt contract as Warm governance/process references.
- WP-017X produced a legacy documentation currency snapshot and conservative
  cleanup/deprecation plan; no physical cleanup was performed.
- WP-017Y completed no-risk legacy docs pointer cleanup by adding status headers
  and safer source-of-truth pointers; no physical cleanup was performed.
- WP-017Z added Warm workflow role cards and a role handoff protocol for the
  repo-native agent workflow; no runtime agents or automation were created.
- WP-017K promoted Real Data Onboarding / Bulk Demo Usage to `v0.9` with
  warnings.
- WP-017Z1 added explicit invocation modes and output modes for future
  repo-native agent prompts; this did not change product status.
- WP-017Z2 added a control-plane protection policy for governance docs; this
  did not change product status.

## Current Blockers And Limitations

- Match playlist mode is not accepted as exact in `v0.9`. Current persisted data distinguishes parser/import provenance (`demo`) and generic Valve share-code provenance (`Valve Matchmaking`), but it does not reliably distinguish Premier, Competitive, Wingman, Casual, Deathmatch, FACEIT or custom modes.
- No playlist-specific claims, filters or recommendations are accepted in `v0.9` unless a future WP captures reliable mode metadata.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1`; no cap raise is accepted by WP-017K.
- Authenticated owner-browser timing remains uncaptured by Codex evidence.
- `/coach` artifact overview is acceptable at 22 demos but should be optimized before materially larger demo volume.
- Historical queued non-parent Steam jobs `#1` and `#10` remain.
- Legacy recommendations `#1`, `#3` and `#4` must not receive new hard evaluations unless explicitly refreshed by a future WP.
- Weak metrics remain caveated; recommendation evaluations must include `metric_confidence`.
- Raw demos and manual backups remain on root-backed storage; do not delete, move or compress raw demos without explicit storage WP authorization.
- Friends/public readiness remains blocked.

## Do Not Do Now

- Do not run live Steam/Valve import, parser jobs, evaluator jobs or manual evaluator unless the current WP explicitly authorizes them.
- Do not mutate production DB, schema, production files or generated app reports unless the current WP explicitly authorizes them with backup/SHA evidence.
- Do not raise `STEAM_IMPORT_MAX_DEMOS_PER_RUN` without an explicit cap-change WP.
- Do not start or change WP-018 product work without an explicit WP-018 prompt.
- Do not start major WP-018/CS2 feature expansion until the foundation
  readiness gate passes; narrow evidence-backed calibration/docs/tests work is
  allowed only when it does not worsen foundation readiness.
- Do not run `git add`, commit or push without explicit user approval.

## Source Of Truth

- Root operating contract: `AGENTS.md`.
- Current state: this file.
- WP order, dependencies and promotion gates: `docs/project_management/WP_REGISTRY.md`.
- New-session bootstrap: `docs/HANDOFF.md`.
- Operating protocol: `docs/project_management/PROJECT_OPERATING_PROTOCOL.md`.
- Agent workflow: `docs/project_management/AGENT_WORKFLOW.md` as Warm governance
  process, control-plane protection, invocation/output mode, task routing and
  prompt contract reference, not per-task Hot context.
- Agent role cards: `docs/agents/roles/*` as Warm role definitions, not
  per-task Hot context.
- Full human WP campaign map: `docs/project_management/MASTER_WP_CHECKLIST.md`.
- Detailed evidence: relevant `docs/audit/WP_*.md` reports, read only when task-relevant.
- Agentic-readiness audit and recovery plan:
  `docs/audits/2026-07-06-agentic-readiness-audit/` and
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/`.
- Foundation risk register:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`.
- Roadmap/planning detail: `docs/project_management/VERSION_ROADMAP.md`, `docs/project_management/WORK_PACKAGE_BACKLOG.md`, `docs/project_management/ACCEPTANCE_MATRIX.md`.
