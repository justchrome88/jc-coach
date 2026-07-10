# WP Registry

Last updated: 2026-07-11.

This is the canonical work-package registry for JC Coach. It preserves WP
history and prevents silent WP ID reuse, skipped prerequisites or promotion
drift. `docs/PROJECT_CONTROL.md`, `docs/HANDOFF.md`,
`docs/CURRENT_STATUS.md`, `WORK_PACKAGE_BACKLOG.md`,
`ACCEPTANCE_MATRIX.md` and `VERSION_ROADMAP.md` must stay aligned with this
registry.

## Governance Rules

- `AGENTS.md` must exist before WP work starts.
- `docs/project_management/WP_REGISTRY.md` must exist before roadmap or
  promotion work starts.
- WP IDs must not be silently reused for a different objective.
- If a planned WP is skipped, it must be marked `deferred` or `superseded` here
  with the reason and the accepting report.
- Promotion WPs must verify all registry prerequisites before promotion.
- `v0.9` promotion must verify `WP-017I` and `WP-017J` evidence. `WP-017J`
  accepted explicit deferral, so promotion may proceed only through `WP-017K`
  with the documented limitation carried forward.
- Historical emergency repair WPs remain in the registry. They were inserted
  because the Steam-path automatic recommendation evaluation trigger became a
  blocker during WP-017.
- `docs/audit/WP_018_DOCUMENTATION_GOVERNANCE_AUDIT_REPORT.md` is an
  out-of-band governance audit evidence file. It does not consume or replace
  the planned `WP-018` product work-package ID.
- GATE-002 authorizes
  `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` as a controlled implementation lane.
  This relaxes the old broad pause only for explicitly scoped MVP WPs and does
  not relax production DB/schema/data mutation, live import, parser/evaluator
  jobs, raw demo lifecycle, public/friends readiness, unsupported coach claims,
  git push restrictions or the Steam import cap.

## Status Values

Allowed statuses: `planned`, `not_started`, `active`, `in_progress`, `done`,
`blocked`, `deferred`, `failed`, `superseded`, `out-of-band evidence`.

## Current Mission Backend And H01 User Acceptance Sequence

| Task ID | Status | Evidence / commit | Current routing |
|---|---|---|---|
| F09 | completed_with_warnings | PM report/artifact; Markdown operation reference corrected to parser artifact 90 | Historical acceptance evidence; no UI/API authorization. |
| F10A_MISSION_PROGRESS_SAMPLE_AND_OBSERVATION_SEMANTICS_REPAIR | accepted | Product 7ee53e3d5ee04a63a5c7dc43803025c0f7d68dc7; PM f4bf9596474f9a0950ac31221b419b8dc246f6c7 | Canonical unique-match sample semantics. |
| F10B_UTILITY_MISSION_TREND_AND_DEFICIENCY_SEMANTICS_REPAIR | accepted | Product 6925c5b9409b3ab1154938e49e2f5e11dbcd868e; PM ffc2ba8c1043990a726be268462fa786904041f7 | Utility mission requires a personal negative trend. |
| F10C_F09_EVIDENCE_AND_CONTROL_PLANE_RECONCILIATION | completed | Documentation/control-plane only | Reconciled current routing; no runtime change. |
| F10D_FINAL_REAL_MISSION_BACKEND_ACCEPTANCE_RERUN | accepted_with_warnings | PM report and sanitized JSON artifact | Real owner-data acceptance passed; known Starlette warning only. |
| G01_OWNER_SYNC_AND_COACH_HEADLESS_VERTICAL_CYCLE | accepted_with_warnings | Product service/CLI/tests and PM G01 report | Canonical owner sync is idempotent, owner-key locked and accepted; known Starlette warning only. |
| G02_THIN_MANUAL_WEB_ADAPTER_AND_RAW_RESULT_VIEW | accepted_with_warnings | Product batch coordinator/web tests and PM G02 report | Durable owner batch lease; G01-only bounded continuations; exact target-31 fixture and restart recovery passed; known Starlette warning only. |
| H01A_FRESH_MATCH_USER_ASSISTED_VERTICAL_CYCLE_ACCEPTANCE | accepted_with_warnings | Product temp-cleanup fix/tests; PM H01A report and JSON artifact | Fresh owner match completed acquisition through honest mission progress; repeat/headless/double-submit were idempotent; known Starlette warning only. |
| H01A-R00_CANONICAL_HOT_ROUTE_RECONCILIATION | completed | Documentation/control-plane reconciliation | Canonical product and PM routing now points to H01A-R01; no runtime or DB change. |
| H01A-R01_LEGACY_PENDING_STEAM_HISTORY_BASELINE_CLASSIFICATION_REPAIR | accepted_with_warnings | Product classification/batch services and focused tests; PM H01A-R01 report | Restored 54+9 production baseline no-op; fresh/deeper discovery and target-31 behavior preserved; known Starlette warning only. |
| H01A-R02_AUTHENTICATED_OWNER_STEAM_LINEAGE_RECONCILIATION | blocked | PM blocked report/artifact | Identity equivalence and migration were proven, then restored because remote preview and persisted dry-run were incorrectly treated as contradictory. |
| H01A-R02A_FRESH_MATCH_DISCOVERY_EVIDENCE_CONTRACT_RECONCILIATION | accepted_with_warnings | Product discovery/reconciliation services and tests; PM H01A-R02A report/artifact | Contract A accepted; owner 17 reconciled; fresh remote identity remains unconsumed; known Starlette warning only. |

CURRENT_LANE: H01_USER_ACCEPTANCE. CURRENT_TASK: none. Mission backend status:
ACCEPTED_FOR_UI_API. H01A_STATUS: PASS_WITH_WARNINGS.
H01A_R02_STATUS: BLOCKED. H01A_R02A_STATUS: PASS_WITH_WARNINGS.
FRESH_DISCOVERY_EVIDENCE_CONTRACT_RECONCILED: true.
AUTHENTICATED_OWNER_STEAM_LINEAGE_RECONCILED: true.
OWNER_SCOPE_CONSISTENT: true. FRESH_MATCH_PRESERVED_FOR_H01A: false.
FRESH_MATCH_READY_AND_UNCONSUMED: false.
FRESH_MATCH_VERTICAL_CYCLE_ACCEPTED: true.
SINGLE_MATCH_REPEAT_IDEMPOTENT: true.
H01A_R01_STATUS: PASS_WITH_WARNINGS.
LEGACY_PENDING_BASELINE_CLASSIFICATION_REPAIRED: true.
ORDINARY_BASELINE_NO_OP_RESTORED: true.
FRESH_MATCH_DISCOVERY_PRESERVED: true.
DEEPER_HISTORY_TRAVERSAL_PRESERVED: true.
BATCH_31_COMPATIBILITY_PRESERVED: true. NEXT_TASK:
H01B_THREE_MATCH_MISSION_PROGRESS_USER_ACCEPTANCE.
Owner-only personal scope, fail-closed weak evidence, no public/friends
readiness and no v1.0 claim remain mandatory.

## WP-017 Canonical Order

| WP ID | Title | Version target | Status | Report path | Dependencies | Notes / warnings |
|---|---|---|---|---|---|---|
| `WP-017A` | Real Data Onboarding / Bulk Demo Usage Diagnosis | `v0.9` | `done` | `docs/audit/WP_017A_REAL_DATA_ONBOARDING_DIAGNOSIS.md` | `v0.8` promoted | Diagnosed storage/import/data state; match mode remained unknown. |
| `WP-017B` | Controlled Bulk Import Plan / Guard Settings | `v0.9` | `done` | `docs/audit/WP_017B_CONTROLLED_BULK_IMPORT_PLAN_REPORT.md` | `WP-017A` | Planned one-demo cap runbook; no live work. |
| `WP-017C` | First Controlled Bulk Import Batch / No-New Path | `v0.9` | `done` | `docs/audit/WP_017C_FIRST_CONTROLLED_BULK_IMPORT_BATCH_REPORT.md` | `WP-017B`, explicit live authorization | One authorized `steam_import_all` no-new path; no demo/parser/evaluation. |
| `WP-017C2` | Controlled Import After New Match / One-Demo Batch-Cap Path | `v0.9` | `done` | `docs/audit/WP_017C2_CONTROLLED_IMPORT_AFTER_NEW_MATCH_REPORT.md` | `WP-017C`, new real match, explicit live authorization | Imported match `#75`; manual evaluation exposed auto-evaluation blocker; cap stayed `1`. |
| `WP-017D` | Post-Batch Acceptance + Auto-Evaluation Trigger Diagnosis | `v0.9` | `done` | `docs/audit/WP_017D_POST_BATCH_ACCEPTANCE_AND_EVALUATION_TRIGGER_DIAGNOSIS.md` | `WP-017C2` | Accepted batch evidence with repair required; blocked pending `#73` and cap raise. |
| `WP-017E` | Auto-Evaluation Trigger Repair for Steam Batch Import Path | `v0.9` | `done` | `docs/audit/WP_017E_AUTO_EVALUATION_TRIGGER_REPAIR_REPORT.md` | `WP-017D` | Emergency repair WP inserted because automatic evaluation was a blocker. |
| `WP-017F` | Controlled Pending Share Code `#73` Import | `v0.9` | `done` | `docs/audit/WP_017F_CONTROLLED_PENDING_73_IMPORT_REPORT.md` | `WP-017E`, explicit live authorization | Proved repaired path on match `#76`; targeted path lacks parent job metadata. |
| `WP-017G` | Post-Batch Data Integrity Acceptance | `v0.9` | `done` | `docs/audit/WP_017G_POST_BATCH_DATA_INTEGRITY_ACCEPTANCE_REPORT.md` | `WP-017F` | Data integrity accepted with warnings; match mode still provenance-only/unknown. |
| `WP-017H` | Post-Batch Performance Acceptance | `v0.9` | `done` | `docs/audit/WP_017H_POST_BATCH_PERFORMANCE_ACCEPTANCE_REPORT.md` | `WP-017G` | Performance accepted with warnings; authenticated browser timing unavailable. |
| `WP-017I0` | Add Root `AGENTS.md` Project Contract | `v0.9` | `done` | `docs/audit/WP_017I0_ADD_ROOT_AGENTS_PROJECT_CONTRACT_REPORT.md` | `WP-017H` | Added root Codex contract; did not promote `v0.9`. |
| `WP-017R` | Roadmap / WP Registry Governance Repair | `v0.9` | `done` | `docs/audit/WP_017R_ROADMAP_WP_REGISTRY_GOVERNANCE_REPAIR_REPORT.md` | `WP-017I0` | Created registry and blocked promotion until match mode WPs are resolved. |
| `WP-017I` | Match Mode Classification Diagnosis | `v0.9` | `done` | `docs/audit/WP_017I_MATCH_MODE_CLASSIFICATION_DIAGNOSIS_REPORT.md` | `WP-017R` | Persisted data cannot distinguish exact playlist mode; current rows should remain playlist `unknown`. |
| `WP-017J` | Match Mode Explicit Deferral / Unknown Labels | `v0.9` | `done` | `docs/audit/WP_017J_MATCH_MODE_EXPLICIT_DEFERRAL_REPORT.md` | `WP-017I` | Explicit deferral accepted: `v0.9` will not include exact playlist classification. Use `mode_unknown`, `provenance_demo`, `provenance_valve_matchmaking` and `exact_date_source=steam_gc_match_time`; do not claim Premier/Competitive/Wingman/Casual/Deathmatch/FACEIT/custom without future reliable metadata. |
| `WP-017S` | Documentation Governance Entrypoint Repair | `v0.9` | `done` | `docs/audit/WP_017S_GOVERNANCE_ENTRYPOINT_REPAIR_REPORT.md` | `WP-017J`, out-of-band governance audit evidence | Service governance repair before promotion lane continues; does not consume planned `WP-018`. |
| `WP-017T` | Compact Current Status and Handoff | `v0.9` | `done` | `docs/audit/WP_017T_COMPACT_CURRENT_STATUS_HANDOFF_REPORT.md` | `WP-017S` | Governance/documentation pass that compresses Hot current-state docs before promotion review; no product logic, DB, service or WP-018 product block changes. |
| `WP-017U` | Project Operating Protocol and Master WP Checklist | `v0.9` | `done` | `docs/audit/WP_017U_PROJECT_OPERATING_PROTOCOL_REPORT.md` | `WP-017T` | Governance/documentation pass that adds the operating protocol and human master WP checklist before promotion review; no product logic, DB, service or WP-018 product block changes. |
| `WP-017V` | Repo-Native Agent Workflow and Docs Steward | `v0.9` | `done` | `docs/audit/WP_017V_AGENT_WORKFLOW_REPORT.md` | `WP-017U` | Governance/documentation pass that adds repo-native WP role workflow and Documentation Steward / Docs Currency Agent; no product logic, DB, service or WP-018 product block changes. |
| `WP-017W` | Task Type Profiles and Prompt Contract | `v0.9` | `done` | `docs/audit/WP_017W_TASK_TYPE_PROFILES_PROMPT_CONTRACT_REPORT.md` | `WP-017V` | Governance/documentation pass that adds task type routing, role invocation shortcuts and Task Card prompt contract; no product logic, DB, service or WP-018 product block changes. |
| `WP-017X` | Legacy Documentation Currency Snapshot | `v0.9` | `done` | `docs/audit/WP_017X_LEGACY_DOCUMENTATION_CURRENCY_SNAPSHOT_REPORT.md` | `WP-017W` | Documentation Steward snapshot of legacy docs and conservative cleanup/deprecation plan; inspection only, no file moves/deletes/archive cleanup, no product logic, DB, service or WP-018 product block changes. |
| `WP-017Y` | No-Risk Legacy Docs Pointer Cleanup | `v0.9` | `done` | `docs/audit/WP_017Y_LEGACY_DOCS_POINTER_CLEANUP_REPORT.md` | `WP-017X` | Documentation/governance pass that adds no-risk status headers and pointer cleanup to legacy docs; no file moves/deletes/archive cleanup, no product logic, DB, service or WP-018 product block changes. |
| `WP-017Z` | Agent Role Cards and Role Handoff Protocol | `v0.9` | `done` | `docs/audit/WP_017Z_AGENT_ROLE_CARDS_HANDOFF_PROTOCOL_REPORT.md` | `WP-017Y` | Governance/documentation pass that adds Warm workflow role cards and a role handoff protocol; no runtime agents/automation, broad legacy cleanup, product logic, DB, service or WP-018 product block changes. |
| `WP-017K` | Real Data Onboarding Promotion to `v0.9` | `v0.9` | `done` | `docs/audit/WP_017K_REAL_DATA_ONBOARDING_PROMOTION_REPORT.md` | `WP-017G`, `WP-017H`, `WP-017I`, `WP-017J` or documented deferral, `WP-017S`, `WP-017T`, `WP-017U`, `WP-017V`, `WP-017W`, `WP-017X`, `WP-017Y`, `WP-017Z` | Promoted `v0.9` with warnings; cap remains `1`, playlist mode remains unknown/provenance-only, and friends/public readiness is not claimed. |
| `WP-017Z1` | Agent Invocation Modes and File-Backed Output Contract | `v0.9` | `done` | `docs/audit/WP_017Z1_AGENT_INVOCATION_OUTPUT_MODES_REPORT.md` | `WP-017Z`, `WP-017K` | Governance/documentation pass that adds invocation modes and output modes to the repo-native agent workflow; no product behavior, DB, service, import/parser/evaluator or WP-018 product implementation changes. |
| `WP-017Z2` | Control Plane Protection Policy | `v0.9` | `done` | `docs/audit/WP_017Z2_CONTROL_PLANE_PROTECTION_POLICY_REPORT.md` | `WP-017Z1` | Governance/documentation pass that protects control-plane docs from ordinary product/code/DB/import/runtime/UI/recommendation task edits; no product behavior, DB, service, import/parser/evaluator or WP-018 product implementation changes. |

## Historical Promotion Gate

`v0.9` promotion completed in WP-017K with `PASS_WITH_WARNINGS`.

Promotion decision carried forward:

- `WP-017I` completed: match mode classification diagnosed.
- `WP-017J` completed with explicit deferral accepted: Match playlist mode is
  not accepted as exact in `v0.9`. Current persisted data distinguishes
  parser/import provenance (`demo`) and generic Valve share-code provenance
  (`Valve Matchmaking`), but it does not reliably distinguish Premier,
  Competitive, Wingman, Casual, Deathmatch, FACEIT or custom modes. No
  playlist-specific claims, filters or recommendations are accepted in `v0.9`
  unless future WPs capture reliable mode metadata.
- Existing WP-017G/H warnings carried forward.
- `WP-017S` completed: governance entrypoints repaired and `WP-018` audit
  naming conflict documented as out-of-band evidence.
- `WP-017T` completed: active current-state and handoff docs compressed so
  future prompts can stay short while current project truth remains in-repo.
- `WP-017U` completed: practical project operating protocol and human master WP
  checklist exist before promotion review.
- `WP-017V` completed: repo-native WP role workflow and Documentation Steward
  checks exist as Warm governance references before promotion review.
- `WP-017W` completed: task type profiles, role invocation shortcuts and Task
  Card prompt contract exist as Warm governance references before promotion
  review.
- `WP-017X` completed: legacy documentation currency snapshot exists before
  promotion review; no physical cleanup was performed.
- `WP-017Y` completed: no-risk legacy pointer cleanup added status headers and
  safer source-of-truth pointers; no physical cleanup was performed.
- `WP-017Z` completed: Warm workflow role cards and role handoff protocol exist
  before promotion review; no runtime agents or automation were created.
- `WP-017K` completed: Real Data Onboarding / Bulk Demo Usage promoted to
  `v0.9` with warnings.
- `WP-017Z1` completed: invocation modes and file-backed output contract exist
  for future short prompts.
- `WP-017Z2` completed: control-plane docs are protected from ordinary product
  task edits unless explicitly scoped by a governance/control-plane task.
- Cap remains `1` unless a separate explicit cap-change WP authorizes a change.

## Foundation Hardening Overlay

The 2026-07-06 agentic-readiness audit is registered as a foundation hardening
overlay, not as a replacement for a planned product WP.

- Audit folder:
  `docs/audits/2026-07-06-agentic-readiness-audit/`.
- Recovery plan:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/`.
- Risk register:
  `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`.
- Audit score: `66%` readiness (`3.30/5` across 106 rows).
- Project status: `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`.
- FH-124R-03 accepted H1 final-readiness rerun evidence: full-suite pytest
  passed, the local quality gate passed and project-gate checks passed.
- FH-125_128 H2 closes the foundation-hardening sequence into a handoff state,
  not product-development authorization.
- Major CS2 feature work, including unrestricted WP-018 expansion, remains
  paused. PF-STAB-01 authorizes only the scoped AI coach quality lane, and
  GATE-002 separately authorizes the controlled MVP auth/import/parser/AI coach
  lane.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO` for unrestricted major CS2
  work, public/friends readiness and `v1.0` claims; docs-only roadmap edits, H1
  PASS evidence and H2 closure do not set it to `YES`. This flag does not block
  scoped WPs inside `MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE` when the WP includes
  the required authorization and evidence contract.
- Required next lane after H2:
- Post-foundation audit/stabilization result:
  `POST-FOUNDATION-01_DEFECT_WARNING_AUDIT_AND_STABILIZATION_PLAN` produced
  `PASS_WITH_WARNINGS`.
- WP-018 restart authorization:
  `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK` authorizes only a
  narrow AI coach quality/calibration/output-quality restart lane. Unrestricted
  WP-018 expansion and major CS2 feature work remain paused.
- Small/scoped work may continue only when it strengthens documentation,
  tests/evals, gates, confidence/caveats or foundation readiness and does not
  add unsupported CS2/domain claims.

## Historical / Superseded MVP_AUTH_IMPORT_PARSER_AI_COACH_LANE

Lane authorization: user decision after GATE-001, recorded by
`GATE-002_MVP_LANE_AUTHORIZATION_AND_GUARDRAIL_UPDATE`.

Lane scope:

- auth / Steam identity;
- import;
- demo storage;
- parser;
- normalized events;
- derived context;
- metric snapshots;
- AI Scout;
- Evidence Validator;
- missions;
- coach UI.

Lane guardrails:

- No production DB/schema/data mutation unless the task explicitly authorizes
  it and includes backup plus pre/post SHA evidence.
- No live Steam/Valve import unless the task explicitly authorizes it.
- No parser/evaluator/manual evaluator jobs unless the task explicitly
  authorizes them.
- No raw demo delete/move/compress unless a storage WP explicitly authorizes
  it.
- No public/friends readiness.
- No unsupported coach claims.
- No git push.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` unless a future cap-change WP
  changes it.

Planned/active sequence:

| WP ID | Title | Status | Report path | Dependencies | Notes / warnings |
|---|---|---|---|---|---|
| `GATE-002` | MVP Lane Authorization and Guardrail Update | `done` | `docs/audit/GATE_002_MVP_LANE_AUTHORIZATION_AND_GUARDRAIL_UPDATE.md` | `GATE-001`, user decision | Docs-only control-plane update. Converts broad stop-signals into controlled implementation gates. |
| `MVP-001` | Auth / Steam Identity Foundation and Guardrails | `planned / next active scoped task` | TBD | `GATE-002` | Owner-only identity scope. No public/friends readiness. Must not launch import/parser/evaluator jobs unless separately authorized. |
| `MVP-002` | Import and Demo Storage Safety Contract | `planned` | TBD | `MVP-001` | Define tempdir, cap, retention and raw-demo lifecycle guardrails. No raw demo delete/move/compress unless explicitly authorized. |
| `MVP-003` | DB / Schema / Data Storage Mutation Plan | `planned` | TBD | `MVP-002` | Any production DB/schema/data mutation requires explicit authorization, backup and pre/post SHA evidence. |
| `MVP-004` | Controlled Steam Import Execution Slice | `planned` | TBD | `MVP-002`, `MVP-003` if DB mutation is needed | Live Steam/Valve import requires explicit authorization. Import cap remains `1` unless a future cap-change WP changes it. |
| `MVP-005` | Parser and Normalized Events Ingestion Slice | `planned` | TBD | `MVP-003`, `MVP-004` if using fresh demos | Parser jobs and production data writes require explicit authorization and evidence. |
| `MVP-006` | Derived Context and Metric Snapshots | `planned` | TBD | `MVP-005` | Must preserve weak-metric caveats and metric-confidence limitations. |
| `MVP-007` | AI Scout and Evidence Validator Integration | `planned` | TBD | `MVP-006`, scoped WP-018 quality infrastructure as needed | Must preserve evidence chains and avoid unsupported coach claims. |
| `MVP-008` | Missions and Coach UI Integration | `planned` | TBD | `MVP-007` | Personal MVP UI only. No public/friends readiness or `v1.0` claim. |
| `MVP-009` | Personal MVP Lane Acceptance Review | `planned` | TBD | `MVP-001` through `MVP-008` or documented deferrals | May only accept scoped personal MVP readiness with carried limitations. Public/friends readiness remains blocked. |

## Historical / Superseded WP-018 Scope

WP-018 preparation/prelude is completed. This does not mark `WP-018` complete
and does not promote `v0.10`.

Completed prelude evidence:

- `WP-018-01_AI_COACH_QUALITY_BASELINE_AND_GAP_MAP`
- `WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`
- `WP-018-03_AI_COACH_DOMAIN_CONSTRAINTS_IN_RUNTIME_PAYLOAD`
- `WP-018-04_AI_COACH_SEMANTIC_VALIDATOR_CONTRACT`
- `WP-018-05_AI_COACH_OUTPUT_QUALITY_ACCEPTANCE_FIXTURES`
- `WP-018-PRELUDE-CLOSE_QUALITY_INFRASTRUCTURE_READY`

Quality infrastructure now available for real WP-018 work:

- version/snapshot metadata;
- runtime CS2 domain constraints;
- semantic validator checks;
- safe fallback behavior;
- accepted/rejected output-quality fixtures.

Next active scoped task: `WP-018A_COACH_OUTPUT_QUALITY_DIAGNOSIS`.

Canonical WP-018A-J sequence remains:

| WP ID | Title | Status |
|---|---|---|
| `WP-018A` | Coach Output Quality Diagnosis | `planned / next active scoped task` |
| `WP-018B` | Recommendation Category Quality Review | `planned` |
| `WP-018C` | Survival Recommendation Calibration | `planned` |
| `WP-018D` | Aim Recommendation Calibration | `planned` |
| `WP-018E` | Utility / Grenade Recommendation Calibration | `planned` |
| `WP-018F` | Map-Specific Recommendation Calibration | `planned` |
| `WP-018G` | Weak Metric Claim Suppression Review | `planned` |
| `WP-018H` | Coach Explanation / Actionability Repair | `planned` |
| `WP-018I` | 5-10 Match Real Usage Acceptance | `planned` |
| `WP-018J` | Promote Coach Quality Calibration to v0.10 | `planned` |

Can-carry warnings:

- Starlette/TestClient deprecation warning remains known.
- Provider-specific structured response enforcement remains shallow.
- Deterministic semantic checks are not a full entailment proof.
- Wording calibration remains future WP-018 work.
- No `v1.0` claim, public/friends readiness, major CS2 expansion, Steam import
  cap raise, playlist/mode certainty or weak-metric hardening is accepted.
- DB/schema/data/import/parser/evaluator/runtime/deploy/package work still
  requires explicit task scope.

## Future Version Registry

| WP ID | Title | Version target | Status | Report path | Dependencies | Notes / warnings |
|---|---|---|---|---|---|---|
| `WP-018` | Coach Quality Calibration | `v0.10` | `planned / restart-authorized for scoped AI coach quality lane` | TBD | `WP-017K` promotion, `WP-017Z1`/`WP-017Z2` governance workflow updates, 2026-07-06 foundation hardening closure, `POST-FOUNDATION-01` audit/stabilization `PASS_WITH_WARNINGS`, `PF-STAB-01` restart scope lock, completed WP-018 preparation/prelude layer | Calibrate coach claims, output quality, progress scoring and weak-metric caveats. Restart is authorized only for narrow AI coach quality/calibration/output-quality tasks. Major coach/domain expansion remains paused; do not mark WP-018 complete, promote `v0.10` or claim full CS2 readiness. Next active scoped task: `WP-018A_COACH_OUTPUT_QUALITY_DIAGNOSIS`. |
| `WP-019` | Personal Daily Use UX | `v0.11` | `planned` | TBD | `WP-018` | Daily owner workflow polish without friends/public claims. |
| `WP-020` | Deployment / Backup / Storage Hardening | `v0.12` | `planned` | TBD | `WP-019` | VPS operation, backup/restore and storage hardening. |
| `WP-021` | Personal MVP Lock | `v1.0` | `planned` | TBD | `WP-020` | Controlled personal MVP lock; public/friends readiness remains separate. |
