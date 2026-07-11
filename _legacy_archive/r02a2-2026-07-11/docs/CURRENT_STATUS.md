# Current Status

Last updated: 2026-07-11.

## Current H01 Metric Assurance State

- CURRENT_LANE: AI_COACH_PRODUCT_COMPLETION.
- CURRENT_TASK: none.
- H01A_STATUS: PASS_WITH_WARNINGS.
- H01A_M01_STATUS: PASS_WITH_WARNINGS.
- H01A_M02_STATUS: PASS_WITH_WARNINGS.
- H01A_M03_STATUS: PASS_WITH_WARNINGS.
- H01A_M04_STATUS: PASS_WITH_WARNINGS.
- COACH_DOMAIN_REQUIREMENTS_MAPPED: true.
- COACH_METRIC_PACK_V1_IMPLEMENTED: true.
- COACH_METRIC_PACK_V1_PRODUCTION_ACCEPTED: true.
- CURRENT_COACH_DOMAIN_METRICS_VALIDATED: true.
- ADR_VALIDATED: true.
- KAST_VALIDATED: true.
- EFFECTIVE_UTILITY_METRICS_VALIDATED: true.
- METRIC_CONTRACTS_VERSIONED: true.
- METRIC_VALIDATION_GATE_IMPLEMENTED: true.
- MATCH_124_GOLDEN_FIXTURE_PASS: true.
- COACH_REJECTS_UNVALIDATED_METRICS: true.
- PRODUCTION_BACKFILL_PERFORMED: true.
- METRIC_PRODUCTION_MIGRATION_COMPLETE: true.
- METRIC_TRUSTED_SUBSET_ACCEPTED: true.
- GLOBAL_METRIC_CORRECTNESS_ACCEPTED: false.
- COACH_VALIDATED_INPUT_GATE_ACTIVE: true.
- ACTIVE_MISSION_INPUTS_VALIDATED: true.
- MATCH_124_GROUND_TRUTH_ACCEPTED: true.
- METRIC_SOURCE_OF_TRUTH_INVENTORIED: true.
- METRIC_DOCUMENTATION_CANONICALIZED: true.
- MATCH_124_FORENSIC_AUDIT_COMPLETE: true.
- METRIC_CORRECTNESS_ACCEPTED: false.
- COACH_INPUTS_TRUSTED: true.
- H01B_STATUS: PASS_WITH_WARNINGS.
- H01B_R01_STATUS: PASS_WITH_WARNINGS.
- H01B_R02_STATUS: PASS_WITH_WARNINGS.
- AI_HYPOTHESIS_ENGINE_ACTIVE: true.
- REAL_MODEL_PATH_ACCEPTED: true.
- THIRTY_MATCH_BASELINE_CONTRACT_ACCEPTED: true.
- TEMPORAL_SURVIVAL_METRICS_ACCEPTED: true.
- EVIDENCE_GROUNDED_OUTPUT_VALIDATION_ACTIVE: true.
- DOMAIN_SLOT_COUNT_PER_OWNER: 2.
- CROSS_DOMAIN_PROPOSALS_ALLOWED: true.
- ONE_ACTIVE_MISSION_PER_DOMAIN_CAPABILITY: true.
- AUTO_ACTIVATION_PERFORMED: false.
- CANONICAL_COACH_DOMAINS: impact_leak, bad_fight_selection.
- COACH_METRIC_GROUPS: performance, utility, aim.
- THIRD_DOMAIN_BLOCKED: true.
- MISSION_3_RECONCILED: true.
- TEN_MATCH_REPLAY_ACCEPTED: true.
- TEN_STATE_RECOVERY_MATRIX_ACCEPTED: true.
- IMPACT_LEAK_ACCEPTED: true.
- BAD_FIGHT_SELECTION_ACCEPTED: true.
- FULL_VERTICAL_CYCLE_ACCEPTED: true.
- H01A_R02_STATUS: BLOCKED.
- H01A_R02A_STATUS: PASS_WITH_WARNINGS.
- FRESH_DISCOVERY_EVIDENCE_CONTRACT_RECONCILED: true.
- AUTHENTICATED_OWNER_STEAM_LINEAGE_RECONCILED: true.
- OWNER_SCOPE_CONSISTENT: true.
- FRESH_MATCH_READY_AND_UNCONSUMED: false.
- FRESH_MATCH_PRESERVED_FOR_H01A: false.
- FRESH_MATCH_VERTICAL_CYCLE_ACCEPTED: true.
- SINGLE_MATCH_REPEAT_IDEMPOTENT: true.
- H01A_R01_STATUS: PASS_WITH_WARNINGS.
- LEGACY_PENDING_BASELINE_CLASSIFICATION_REPAIRED: true.
- ORDINARY_BASELINE_NO_OP_RESTORED: true.
- FRESH_MATCH_DISCOVERY_PRESERVED: true.
- DEEPER_HISTORY_TRAVERSAL_PRESERVED: true.
- BATCH_31_COMPATIBILITY_PRESERVED: true.
- MISSION_BACKEND_STATUS: ACCEPTED_FOR_UI_API.
- MISSION_BACKEND_ACCEPTED_FOR_UI_API: true.
- F10D_STATUS: PASS_WITH_WARNINGS.
- G01_STATUS: PASS_WITH_WARNINGS.
- HEADLESS_OWNER_COACH_SYNC_CONTRACT_ACCEPTED: true.
- OWNER_SYNC_IDEMPOTENT: true.
- OWNER_SYNC_CONCURRENCY_GUARDED: true.
- G02_STATUS: PASS_WITH_WARNINGS.
- OWNER_SYNC_BATCH_COORDINATOR_ACCEPTED: true.
- SUCCESSFUL_TARGET_31_SUPPORTED: true.
- EXACT_STOP_AT_TARGET_PROVEN: true.
- BATCH_RESTART_RECOVERY_PROVEN: true.
- THIN_OWNER_SYNC_WEB_ADAPTER_ACCEPTED: true.
- WEB_ADAPTER_USES_HEADLESS_CONTRACT: true.
- DOUBLE_SUBMIT_DUPLICATION_BLOCKED: true.
- NEXT_TASK: H01B-R03_TWO_MISSION_CARDS_ACTIVATION_AND_MATCH_FEEDBACK_UI.
- ACTIVE_OUTBOX_TASK: none.
- H01B-R02 accepted the configured `gpt-5.6-sol` reasoning path, immutable
  owner-17 30-match baseline, append-only temporal survival evidence, strict
  claim/target validation, two independent proposal-ready domain slots, and
  production repeat no-op. No mission was auto-activated.
- H01B-R01 corrected the M04 naming drift: `impact_leak` and
  `bad_fight_selection` are the only coach domains, while performance/utility/
  aim remain metric groups. `utility_value` is context-only. Mission 3 and all
  of its lineage remain preserved but it is cancelled with
  `noncanonical_domain_reconciliation`; production honestly has zero active
  missions. The ten-match isolated replay, S1-S10 recovery matrix, both-domain
  fixtures, mission selection/progress, full stack, and repeat idempotency pass.
  The accepted Starlette TestClient warning remains.
- H01A-M04 preserved 55 immutable enriched event sets and 165 validated v3
  performance/utility/aim metric-group snapshots, a five-demo golden corpus,
  and repeat no-op. Its historical product-domain and mission-3 conclusions are
  superseded by H01B-R01; its metric-pack evidence remains accepted.
- H01A-M03 preserved 1,153 legacy snapshots, appended 110 owner-only v2
  snapshots across 55 retained artifacts/event sets, accepted the trusted
  match-124 subset, and reconciled historical evidence idempotently. Mission
  3 still requires quarantined `utility_damage`, so H01B remains blocked.
- H01A-M02 versioned critical contracts and append-only snapshot identity,
  repaired phase/core-combat/alias root causes, and enforced validated-only
  owner/coach selection. ADR, KAST, ambiguous damage and legacy utility
  semantics remain explicitly quarantined; H01B remains blocked pending M03.
- H01A-M01 established the canonical `docs/metrics/` registry/contracts and a
  deterministic read-only ledger for match 124. It confirmed post-match event,
  round-participation, raw-damage, snapshot-version and source-selection defects.
  Metric correctness and coach inputs remain unaccepted; H01B is blocked.
- H01A accepted one genuinely fresh owner match through authenticated G02:
  remote discovery, retained demo, owner-linked import, real parser artifact,
  combat/utility snapshots, coach hypotheses and honest
  `insufficient_data` mission progress all completed. Web repeat, headless
  repeat and rapid double-submit created no duplicate domain lineage. A narrow
  acceptance fix now cleans caller-owned download temp files after verified
  retained storage; the full rerun passed with only the accepted Starlette
  TestClient deprecation warning.
- H01A-R02A selected Contract A: remote preview is owner-scoped and
  non-persisting, persisted G01 dry-run remains network-isolated, and real G01
  refreshes canonical Steam history before persisted candidate processing.
  Owner `17` now owns Steam account `1` and all legacy match/mission lineage;
  the production preview still exposes one fresh unconsumed identity.
- H01A-R01 repaired derived owner-sync classification without a schema or
  production-data rewrite. The nine historical pending rows are diagnostic
  `legacy_stale_pending`, the production dry baseline is `success_no_changes`,
  and accepted sync lineage keeps genuinely fresh and deeper matches actionable.
  H01A is now accepted after the fresh-match rerun.
- G01 accepted one owner-scoped headless import-to-coach application service
  and a thin CLI adapter. The service preserves the one-new-demo cap, fails
  closed on owner scope, reuses durable parser/metric/coach state, returns a
  versioned structured result and uses an owner-keyed recoverable DB lease.
- G02 accepted the owner-scoped durable batch coordinator and minimal technical
  web adapter. Each bounded continuation calls only G01; target `31` counts
  only newly completed accepted cycles, stops before a 32nd success, recovers
  stale batch leases and prevents duplicate same-owner starts.
- F10D accepted corrected unique-match samples, personal-negative utility trend
  semantics, owner isolation, mission lifecycle/progress, idempotent real match
  processing, coach payload progress and domain-aware suppression on real owner
  data. The only current F10D warning is the accepted Starlette/TestClient
  deprecation warning.
- F09 remains historical lifecycle evidence; its pre-F10B utility-candidate
  semantics are superseded. F10A/F10B are current truth.
- Owner-only personal scope and fail-closed weak evidence remain mandatory. No
  public/friends readiness or v1.0 claim is authorized.

## Historical Pre-F10 Snapshot

- Product identity: JC Coach remains the primary product. Do not build JC
  Forge unless a future explicit task changes product scope.
- Current organizational mini-phase: `LEAN_DOCS_CLEANUP` /
  `CODEX_NATIVE_SIMPLIFICATION`, closed by `LEAN-DOCS-06`; do not return to
  docs cleanup unless explicitly scoped.
- One Codex workspace convention: start the main Codex working session from
  `/opt/jc-coach`.
- Codex PM, Executor, Reviewer and Documentation Steward are prompt roles in
  the same product workspace unless a future explicit task asks for separate
  windows. They are not mandatory separate Codex sessions.
- Product version: `v0.9`.
- Current lane:
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE`, authorized by user decision after
  GATE-001.
- The scoped WP-018 AI coach quality/calibration/output-quality lane remains
  available, but it is no longer the only authorized post-foundation product
  lane.
- Post-foundation audit/stabilization result:
  `POST-FOUNDATION-01_DEFECT_WARNING_AUDIT_AND_STABILIZATION_PLAN` produced
  `PASS_WITH_WARNINGS`; no broad product/runtime remediation is required before
  a narrow WP-018 restart.
- Current active WP: `WP-018 Coach Quality Calibration` remains open and is
  not complete; the preparation/prelude layer is closed.
- Next scoped task: `WP-018A_COACH_OUTPUT_QUALITY_DIAGNOSIS`.
- WP-018 is restart-authorized only for narrow AI coach quality, calibration
  and output-quality scope. The new MVP lane is separately authorized for
  explicitly scoped WPs covering auth / Steam identity, import, demo storage,
  parser, normalized events, derived context, metric snapshots, AI Scout,
  Evidence Validator, missions and coach UI.
- Allowed WP-018 work is limited to narrow evidence, caveat, calibration,
  output-quality, docs or tests work that improves coach quality and does not
  add unsupported coach/domain claims.
- Promotion status: `v0.9` is promoted with warnings by WP-017K. Warnings and limitations must carry forward into WP-018.
- MVP lane status: authorized for controlled implementation WPs only. Each
  future WP must name allowed files, risk scope, required backup/SHA evidence
  where applicable, import/parser/evaluator authorization if applicable and a
  file-backed report.
- Latest known production DB SHA: `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33` from read-only project-gate evidence. Re-check before any WP that depends on current DB state.

## Historical Foundation Hardening Status

- 2026-07-06 read-only agentic-readiness audit result: `66%` readiness
  (`3.30/5` across 106 audit rows).
- Audit decision: `YES, BUT` - continue only small/scoped work while fixing
  foundation P0/P1 items before major coach/domain expansion.
- Recovery plan:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/`.
- Foundation risk register:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`.
- Current project status for execution planning:
  `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK`: `NO` for unrestricted major CS2 feature
  work, public/friends readiness and `v1.0` claims. This flag no longer blocks
  the explicitly authorized `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` when a
  future WP provides scope, evidence requirements and explicit authorization
  for risky actions.
- FH-124R-03 accepted H1 final-readiness rerun evidence with full-suite pytest
  `250 passed, 1 warning`, local quality gate `LOCAL_QUALITY_GATE=PASS` and
  project-gate checks passing. H2 closes the foundation-hardening sequence as a
  handoff state, not as product-development authorization.
- Docs-only roadmap edits, H1 PASS evidence and H2 closure do not set
  `READY_FOR_MAJOR_CS2_FEATURE_WORK` to `YES`.
- POST-FOUNDATION-01 completed the post-foundation defect/warning audit and
  stabilization pass with `PASS_WITH_WARNINGS`; PF-STAB-01 scope-locks the
  narrow WP-018 restart path.

## Runtime Basics

- Project path: `/opt/jc-coach`.
- Service: `jc-coach.service`.
- Backend: Python / FastAPI / Uvicorn.
- Bind target: `127.0.0.1:8010`.
- Production DB: `data/cs2_coach.db`.
- Shell service calls that touch Steam/import temp storage must use `TMPDIR=/opt/jc-coach/data/tmp`, `TEMP=/opt/jc-coach/data/tmp` and `TMP=/opt/jc-coach/data/tmp` when explicitly authorized.

## Historical Accepted State

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
- WP-018 preparation/prelude is closed by
  `WP-018-PRELUDE-CLOSE_QUALITY_INFRASTRUCTURE_READY` and
  `WP-018-PRELUDE-DOC-SYNC_QUALITY_INFRASTRUCTURE_CANONICAL_UPDATE`.
- AI coach quality infrastructure now available for real WP-018 work:
  version/snapshot metadata, runtime CS2 domain constraints, semantic
  validator checks, safe fallback behavior and accepted/rejected
  output-quality fixtures.
- GATE-002 authorizes the
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` as a controlled implementation lane,
  not as unrestricted production mutation or public readiness.

## Current Blockers And Limitations

- The lean docs cleanup is organizational work only. It does not authorize JC
  Forge work, major CS2 product work, public/friends access or a `v1.0` claim.
- Foundation hardening is closed only as
  `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`.
- Post-foundation audit/stabilization has passed with warnings. It authorized
  the scoped WP-018 restart for AI coach quality/calibration/output quality,
  and the later GATE-002 user decision authorizes the separate controlled MVP
  implementation lane.
- WP-018 prelude closed the quality-infrastructure blocker, but WP-018 itself
  remains open; do not mark `v0.10` promoted.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK` is not `YES`; unrestricted major CS2
  feature work and unrestricted WP-018 expansion remain paused/blocked. This
  does not block scoped work inside
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` when the task-specific WP carries the
  required authorization and evidence contract.
- System `v1.0` is not claimed. It remains gated behind future post-foundation
  audit/remediation, later roadmap WPs and explicit acceptance.
- AI coach can-carry warnings: Starlette/TestClient deprecation warning remains
  known; provider-specific structured response enforcement remains shallow;
  deterministic semantic checks are not a full entailment proof; wording
  calibration remains future WP-018 work.

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

- Current routing is
  H01B_THREE_MATCH_MISSION_PROGRESS_USER_ACCEPTANCE after accepted H01A, not
  the historical WP-018/MVP routes below. G02
  accepted only the thin technical adapter and durable coordinator; no
  scheduler, public/friends access or v1.0 claim is authorized.

- Do not run live Steam/Valve import, parser jobs, evaluator jobs or manual evaluator unless the current WP explicitly authorizes them.
- Do not mutate production DB, schema, production files or generated app reports unless the current WP explicitly authorizes them with backup/SHA evidence.
- Do not raise `STEAM_IMPORT_MAX_DEMOS_PER_RUN` without an explicit cap-change WP.
- Do not start or change WP-018 product work without an explicit WP-018 prompt;
  the next authorized prompt should start from
  `WP-018A_COACH_OUTPUT_QUALITY_DIAGNOSIS`.
- Do not start unrestricted major WP-018/CS2 feature expansion. Scoped MVP lane
  work may proceed only under
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` WPs that explicitly define files,
  mutation/job authorization, backup/SHA evidence where applicable and a
  file-backed report.
- Do not change DB/schema/data/import/parser/evaluator/runtime/deploy/package
  files unless the active task explicitly scopes that risk.
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
- Final foundation closure / post-foundation handoff report:
  `docs/archive/lean-docs-2026-07-09/from-root/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-125_128_final-foundation-closure-post-foundation-audit-handoff_report.md`.
- Foundation risk register:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`.
- Roadmap/planning detail: `docs/project_management/VERSION_ROADMAP.md`, `docs/project_management/WORK_PACKAGE_BACKLOG.md`, `docs/project_management/ACCEPTANCE_MATRIX.md`.
