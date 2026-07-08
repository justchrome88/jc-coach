# Foundation Hardening Risk Register

Date: 2026-07-06.

Scope: FH-MILESTONE-001 - Readiness Recovery / Foundation Hardening.

Current project status:

```text
CONTINUE WITH RESTRICTED SCOPE
READY_FOR_MAJOR_CS2_FEATURE_WORK: NO
```

This register is the canonical structured risk register for the
2026-07-06 readiness recovery lane. It tracks foundation risks that must be
closed, hard-blocked or explicitly risk-accepted before major CS2 feature work
can resume.

This document does not claim final readiness. It also does not close or
risk-accept any item by itself. Closure, hard-blocker status and risk
acceptance require source evidence in the relevant task report, readiness gate
review or PM approval record.

## Source Evidence

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/00_EXECUTIVE_DECISION.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/02_P0_P1_HARDENING_BACKLOG.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/05_EXECUTION_PLAN.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/07_CODEX_EXECUTION_HANDOFF.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/08_TOP_10_NEXT_ACTIONS.md`

## Field Model

Each risk entry uses these fields:

| Field | Meaning |
|---|---|
| Risk ID | Stable register identifier. For backlog-derived items this mirrors the source hardening task ID. |
| Title | Short risk name suitable for PM review. |
| Criticality | P0, P1, P2 or P3. FH-010 seeds P0/P1 from the current backlog. |
| Layer / category | Product, technical or governance layer affected by the risk. |
| Owner role | Role expected to drive closure or acceptance. This is not an individual assignment. |
| Status | Current conservative state: `Open`, `Partially mitigated`, `Hard-blocked`, `Accepted risk`, `Closed`, `Pending import`, `Superseded` or `Needs clarification`. |
| Target FH task or WP | The hardening task, WP or future task expected to resolve or decide the risk. |
| Source evidence | Source row, document or audit reference that proves the risk exists. |
| Current impact | Why the risk matters now. |
| Required next action | Next concrete action needed to reduce, close or decide the risk. |
| Acceptance / exit condition | Evidence required before the risk can leave `Open`. |
| Notes | Constraints, dependencies, visible blocked work or reporting notes. |

## Status Policy

- No risk is marked `Closed` unless source evidence already proves closure.
- No risk is marked `Accepted risk` unless an explicit acceptance source exists.
- `Partially mitigated` means accepted hardening evidence reduced the risk, but
  remaining work, final-gate verification or explicit acceptance is still
  needed before the risk can be treated as closed for major CS2 feature work.
- `Accepted risk` may be used when the remaining limitation is explicitly
  accepted as visible current-state scope and future work remains blocked or
  gated.
- P0 risks must be closed or explicitly hard-blocked before the readiness gate
  can pass. A `Partially mitigated` P0 remains gate-blocking unless the final
  readiness review explicitly accepts the remaining boundary.
- P1 risks must be closed or have approved workaround and risk acceptance before
  the readiness gate can pass.
- P2/P3 risks are intentionally not imported by FH-010; they remain covered by
  `03_P2_P3_TRIAGE.md` until a later task scopes triage import.

## Active Global Blocks

These blocks remain active across all register entries until the readiness gate
passes or a stricter future source changes the state.

| Blocked area | Current state | Evidence | Register link |
|---|---|---|---|
| Major CS2 feature work | Blocked until `04_READINESS_GATE.md` evaluates to PASS. | `00_EXECUTIVE_DECISION.md`; `04_READINESS_GATE.md`; `WP_REGISTRY.md`. | Affects all P0/P1 risks. |
| Public/friends access | Blocked until security/privacy/ops criteria pass. | FH-P0-002; `04_READINESS_GATE.md`. | `R-FH-P0-002`, `R-FH-P1-032`, `R-FH-P1-033`. |
| Import cap raise / larger Steam demo batches | Blocked unless a separate explicit cap-change WP authorizes it. | `AGENTS.md`; `CURRENT_STATUS.md`; FH-P1-009; Macro-batch A. | `R-FH-P1-007`, `R-FH-P1-009`, `R-FH-P0-001`. |
| Schema-changing product work | Blocked unless explicitly scoped behind migration baseline and DB safety. | FH-P0-001; `04_READINESS_GATE.md`. | `R-FH-P0-001`, `R-FH-P1-016`, `R-FH-P1-028`. |
| Unsupported coach claims | Blocked for weak metrics, playlist-specific mode claims and unsupported CS2/domain recommendations. | `CURRENT_STATUS.md`; FH-P0-003; FH-P1-014 through FH-P1-022. | AI Coach, Metrics and CS2 Domain risks below. |

## P0 Risks

### R-FH-P0-001 - Create Migration Baseline And Schema Gate

| Field | Value |
|---|---|
| Risk ID | R-FH-P0-001 |
| Title | Schema work can drift or mutate production without a migration baseline. |
| Criticality | P0 |
| Layer / category | Web Application Core / Project Instance / DB safety |
| Owner role | DB_GUARDIAN / Execution / QA |
| Status | Hard-blocked |
| Target FH task or WP | FH-P0-001 / FH-030 through FH-037 / future migration-engine or final-gate decision |
| Source evidence | `02_P0_P1_HARDENING_BACKLOG.md` FH-P0-001; audit matrix AR-019, AR-026, AR-067; audit `08_CRITICAL_GAPS.md`; `09_RECOMMENDED_TASKS.md` TASK-AUDIT-001; FH-030 report and commit `ba74606`; FH-031 report and commit `f9d5a94`; FH-032 report and commit `0c37b40`; FH-033 report and commit `c04b03c`; FH-034 report and commit `de21f36`; FH-035 PM review and commit `4041c9a`; FH-036 PM review and commit `3a6990a`; FH-037 report and commit `65fa1f8`; `docs/MIGRATIONS.md`; `docs/BACKUP_RESTORE.md`; FH-125A-01 task-card migration-boundary decision. |
| Current impact | Schema evolution is constrained by a baseline, schema gate, approval policy, SHA discipline, copied-DB workflow and test guards. JC Coach still has no adopted migration engine and no accepted production migration capability. |
| Required next action | Keep schema-changing product work blocked unless a separate migration-engine/schema task is explicitly authorized. Do not claim Alembic, equivalent production migration support or production migration capability. |
| Acceptance / exit condition | For current final-readiness rerun purposes, the no-engine migration scaffold is an explicit visible limitation: baseline/read-only gate exists, production DB remains untouched unless explicitly authorized with backup and before/after SHA evidence, startup helper receives no new schema behavior and schema-changing WPs require explicit migration scope. Full closure still requires a future migration-engine/schema task if schema-changing product work is needed. |
| Notes | FH-030 through FH-037 mitigated the P0 boundary with scaffolding, policy, copied-DB checks and tests, but did not adopt Alembic, add migration support, mutate the production DB, change startup schema behavior or approve major schema-changing product work. FH-125A-01 records the user/PM decision to accept this as a visible no-engine limitation for the next final-readiness rerun while hard-blocking schema-changing product work and any production migration claim. |

### R-FH-P0-002 - Keep Public/Friends Access Blocked Until Security Gate

| Field | Value |
|---|---|
| Risk ID | R-FH-P0-002 |
| Title | Personal-only app could be treated as shareable before security/privacy readiness. |
| Criticality | P0 |
| Layer / category | Web Application Core / Security / Privacy / Ops |
| Owner role | Security / PM / QA |
| Status | Hard-blocked |
| Target FH task or WP | FH-P0-002 |
| Source evidence | `02_P0_P1_HARDENING_BACKLOG.md` FH-P0-002; audit matrix AR-027; audit `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`; audit `00_EXECUTIVE_SUMMARY.md`; Macro-batch G report `FH-110_117_public-readiness-security-deploy-safety-batch_report.md`; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-110_117_review.md`; `CURRENT_STATUS.md`. |
| Current impact | Controlled personal/VPS use is acceptable. Public/friends access is explicitly blocked and current in-memory rate limiting is not public-grade. |
| Required next action | Keep explicit release-gate language blocking public/friends work until security/privacy/ops criteria pass in a future explicitly scoped task. H2/final readiness may report this boundary, but must not open access. |
| Acceptance / exit condition | Public/friends work is visibly blocked in current status, security/deploy/limitations docs and readiness gate; no product access expansion occurs. |
| Notes | Macro-batch G accepted documentation/governance safety evidence for the block. This is not a public-readiness claim: public/friends access, social sharing and public-readiness claims remain blocked until a future explicit gate. |

### R-FH-P0-003 - Design Diagnosis Registry And Recommendation Planner

| Field | Value |
|---|---|
| Risk ID | R-FH-P0-003 |
| Title | Coach may produce plausible advice without verified problem selection. |
| Criticality | P0 |
| Layer / category | AI Coach Product Archetype / Recommendation planning |
| Owner role | Architect / Metrics Guardian / Execution / QA |
| Status | Closed |
| Target FH task or WP | FH-P0-003 |
| Source evidence | `02_P0_P1_HARDENING_BACKLOG.md` FH-P0-003; audit matrix AR-033; audit `08_CRITICAL_GAPS.md`; `09_RECOMMENDED_TASKS.md` TASK-AUDIT-007; Macro-batch F report `FH-100_107_diagnosis-recommendation-planner-design-batch_report.md`; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-100_107_review.md`. |
| Current impact | The diagnosis registry and recommendation planner design contract is accepted at docs/design level, including allowed inputs, weak-metric exclusions, one-primary-focus selection, evidence links and implementation entry criteria. |
| Required next action | Keep runtime planner implementation blocked until an explicit future implementation task and its entry criteria pass. |
| Acceptance / exit condition | Planner design is accepted and implementation entry criteria are explicit; implementation remains gated until metric/source/eval contracts are ready. |
| Notes | Closed for the P0 design requirement only. No planner runtime implementation exists or is claimed, and unsupported coach/domain claims remain blocked. |

## P1 Risks

All P1 risks from `02_P0_P1_HARDENING_BACKLOG.md` are represented below.
Statuses reflect accepted macro-batch evidence and explicit FH-125A-01
limitations after H1 and FH-124R-01. This reconciliation does not claim final
readiness.

| Risk ID | Title | Criticality | Layer / category | Owner role | Status | Target FH task or WP | Source evidence | Current impact | Required next action | Acceptance / exit condition | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R-FH-P1-001 | Expand project gate pre/postflight | P1 | Agentic Core / Tests | TEST_GUARDIAN / Execution | Closed | FH-P1-001 / FH-020 / FH-022 / FH-025 | AR-009; `06_TESTS_EVALS_QUALITY.md`; TASK-AUDIT-002; FH-020 report and commit `17a2b69`; FH-022 report and commit `5e9686e`; FH-025 report and commit `0b7db63`. | Project gate preflight/changed/required-check/postflight evidence and report gate-output rules now exist. | Maintain the gate/report contract in future tasks. | Reports require gate output and local gate evidence according to task class. | Closed for the intended project-gate/reporting scope; enforcement and hosted CI remain covered by `R-FH-P1-003` and `R-FH-P1-029`. |
| R-FH-P1-002 | Create structured risk register | P1 | Agentic Core / Risk tracking | PM / Docs | Closed | FH-P1-002 / FH-010 / FH-012 | AR-015; `03_DOCS_AND_CONTEXT.md`; TASK-AUDIT-003; FH-010 report; FH-011 report; FH-012 report. | Risks now have owner/status/target WP/evidence in one canonical register linked from current docs. | Maintain the register links and update future risk status only through scoped task evidence. | Register is linked from current docs and accepted by PM review. | FH-010 created the artifact, FH-011 verified P0/P1 field coverage and FH-012 linked it from `CURRENT_STATUS.md`, `WP_REGISTRY.md`, `VERSION_ROADMAP.md` and `WORK_PACKAGE_BACKLOG.md`. |
| R-FH-P1-003 | Add automated enforcement of agent rules | P1 | Agentic Core / CI | TEST_GUARDIAN / QA | Accepted risk | FH-P1-003 / FH-023 / FH-024 / FH-096 / FH-097 / FH-124R-01 | AR-016; `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`; FH-023 report and commit `25d2eb2`; FH-024 report and commit `a95fb3f`; Macro-batch E2 report `FH-096_097_eval-gate-integration-readiness-fixtures-batch_report.md`; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-096_097_review.md`; FH-124R-01 recovery report. | Mandatory local CI-equivalent enforcement exists and final-gate focused fixture checks are wired. Hosted CI/branch protection is not configured. | Keep the local gate mandatory; treat missing, failed, stalled or timed-out required checks as blocking. Hosted CI remains future explicit scope if needed. | Local enforcement is accepted as the current workaround for this personal/restricted lane; no hosted CI claim is made. | Accepted local-only limitation, not a hosted-CI closure. H1 still needs rerun and acceptance before final readiness. |
| R-FH-P1-004 | Expand architecture map | P1 | Web Core / Architecture | Architect / Runtime | Closed | FH-P1-004 / FH-040 / FH-041 | AR-017; `04_ARCHITECTURE_CODEBASE.md`; Macro-batch FH-040_041 report; PM review `/opt/jc-coach-pm/reviews/2026-07-07_FH-040_041_review.md`. | Architecture/module/data-flow/mutation boundaries are documented. | Maintain architecture docs when future scoped changes alter boundaries. | Boundaries are inspectable in architecture docs. | Closed for descriptive architecture-map scope. |
| R-FH-P1-005 | Add API contract inventory/tests | P1 | Web Core / API contracts | Runtime / QA | Accepted risk | FH-P1-005 / FH-042 through FH-047 | AR-018; TASK-AUDIT-008; FH-042_043 report; FH-044_047 report and PM recovery review; FH-045_046 report; warning ledger `WL-FH-000-019` and `WL-FH-000-023`. | Core endpoint inventory and first focused endpoint contract tests exist, but live ASGI/TestClient dispatch and deeper validation matrix coverage remain known limitations. | Keep route/API limitations visible; add deeper live ASGI/service validation only under explicit future test/runtime scope. | Practical contract inventory/tests are accepted with known limitations and no public-readiness claim. | Accepted workaround for current readiness rerun; not a claim of complete public/API validation coverage. |
| R-FH-P1-006 | Harden owner/auth edge state | P1 | Web Core / Security | Security / Runtime | Accepted risk | FH-P1-006 / FH-110 through FH-117 | AR-020; `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`; Macro-batch G report `FH-110_117_public-readiness-security-deploy-safety-batch_report.md`; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-110_117_review.md`. | Owner/auth edge state remains constrained to controlled personal use; public/friends expansion remains blocked. | Keep owner/public boundary language visible; add edge-state tests only under future scoped security/runtime work. | Personal-only boundary is accepted and public/friends access remains blocked. | Accepted limitation for current personal lane; no public/friends access work. |
| R-FH-P1-007 | Create job error taxonomy and result_json schema | P1 | Web Core / Import | Import Guardian | Closed | FH-P1-007 / FH-050 / FH-051 | AR-022, AR-029; TASK-AUDIT-010; Macro-batch A report `FH-050_056_import-worker-safety-contracts-batch_report.md`; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-050_056_review.md`. | Import outcome taxonomy and `result_json` schema expectations are documented. | Maintain the contract in future import work. | Outcomes have schema and examples. | Closed at docs/design contract level; no live import or worker implementation was performed. |
| R-FH-P1-008 | Create safe env reference | P1 | Web Core / Ops / Security | Security / Docs | Closed | FH-P1-008 / FH-113 | AR-025; Macro-batch G report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-110_117_review.md`; `docs/SECURITY.md`. | Safe environment references use names and purposes without secret values. | Maintain no-secret-values reporting policy. | Safe reference exists and reveals no secret values. | Closed for safe env reference scope. |
| R-FH-P1-009 | Plan durable worker/retry ledger before cap raise | P1 | Web Core / Ops / Import | Import / Architect | Closed | FH-P1-009 / FH-052 / FH-053 / FH-054 | AR-029; TASK-AUDIT-010; Macro-batch A report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-050_056_review.md`; `AGENTS.md`; `CURRENT_STATUS.md`. | Durable worker and retry-ledger requirements are documented; import cap raise remains blocked. | Do not raise import cap or implement worker/retry behavior without separate explicit task authorization. | Cap raise remains blocked until design plus separate cap-change authorization exists. | Closed for planning/blocking scope only; no worker, retry ledger or cap raise was implemented. |
| R-FH-P1-010 | Create generic AI coach archetype model doc | P1 | AI Coach / Architecture | Architect / Metrics | Closed | FH-P1-010 / FH-080 | AR-031; Macro-batch D report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md`. | Generic AI coach archetype is documented as evidence-bound and subordinate to metric/source/domain contracts. | Maintain separation in future AI coach changes. | Separation is documented. | Closed at docs/contracts level. |
| R-FH-P1-011 | Enforce one primary accepted focus until planner exists | P1 | AI Coach / PM | Metrics / PM | Closed | FH-P1-011 / FH-081 / FH-104 | AR-032; Macro-batch D report; Macro-batch F report; PM reviews `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md` and `/opt/jc-coach-pm/reviews/2026-07-08_FH-100_107_review.md`. | One-primary-focus rule and planner selection logic are documented. | Keep one accepted primary focus until future planner implementation is explicitly scoped and accepted. | One-focus rule is explicit. | Closed for contract/design scope. |
| R-FH-P1-012 | Calibrate progress wording and sample confidence | P1 | AI Coach / Metrics / UI | Metrics / UI / QA | Closed | FH-P1-012 / FH-087 | AR-034; Macro-batch D report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md`. | Progress wording is calibrated for small sample, weak, mixed-source and approximate evidence. | Maintain wording/caveat discipline in future UI/coach work. | Wording matches confidence and sample size. | Closed at docs/contracts level. |
| R-FH-P1-013 | Keep metric_confidence mandatory | P1 | AI Coach / Metrics | Metrics / QA | Closed | FH-P1-013 / FH-084 / FH-095 | AR-035; Macro-batch D report; Macro-batch E1 report; PM reviews `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md` and `/opt/jc-coach-pm/reviews/2026-07-08_FH-090_095_review.md`. | `metric_confidence` remains mandatory for hard recommendation/evaluation/AI coach evidence where applicable. | Keep missing confidence demoted or blocked in future hard-evidence paths. | Missing confidence fails or demotes evidence according to accepted contracts/evals. | Closed for current contract/eval scope. |
| R-FH-P1-014 | Create coach advice confidence contract | P1 | AI Coach / Metrics | Metrics / Architect | Closed | FH-P1-014 / FH-082 / FH-088 | AR-036; Macro-batch D report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md`. | Advice confidence contract is documented as the weakest supported evidence link. | Maintain the confidence contract in future coach output work. | Advice confidence contract is accepted. | Closed at docs/contracts level. |
| R-FH-P1-015 | Add evidence link model | P1 | AI Coach / Explainability | Metrics / Architect | Closed | FH-P1-015 / FH-083 / FH-105 | AR-037; Macro-batch D report; Macro-batch F report; PM reviews `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md` and `/opt/jc-coach-pm/reviews/2026-07-08_FH-100_107_review.md`. | Problem -> metric -> match/window -> recommendation evidence chain is documented. | Preserve evidence links for future hard advice and planner work. | Chain is required for hard advice. | Closed at docs/contracts/design level. |
| R-FH-P1-016 | Add prompt/payload versioning | P1 | AI Coach / Reproducibility | Metrics / Execution / QA | Accepted risk | FH-P1-016 / FH-085 / FH-086 | AR-038; TASK-AUDIT-005; Macro-batch D report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md`; FH-125A-01 no-engine schema boundary. | Prompt/payload version contract and versioned snapshot plan are documented, but no runtime persistence/schema change was implemented. | Keep runtime persistence/schema work blocked unless explicitly scoped behind schema/migration authorization. | Accepted no-schema workaround exists for current readiness rerun. | Accepted limitation; future reproducibility persistence remains gated by schema boundary. |
| R-FH-P1-017 | Build semantic AI eval suite | P1 | AI Coach / Tests | QA / Metrics | Closed | FH-P1-017 / FH-090 through FH-097 / FH-124R-01 | AR-039, AR-088; TASK-AUDIT-006; Macro-batch E1 report and PM review; Macro-batch E2 report and PM review; FH-124R-01 recovery report. | Deterministic local semantic AI eval suite and final-gate visibility exist; FH-124R-01 proved current focused and full-suite paths pass outside H1. | Keep semantic evals in local gate/final readiness checks. | Eval suite blocks overclaim cases. | Closed for current eval baseline; H1 final readiness still requires rerun/acceptance. |
| R-FH-P1-018 | Add CS2 match/round domain map | P1 | CS2 Domain / Docs | Docs / Metrics | Closed | FH-P1-018 / FH-060 through FH-069 | AR-043; TASK-AUDIT-009; Macro-batch B report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-060_069_review.md`. | CS2 match/round/source/domain boundary map exists. | Maintain the domain contract and avoid unsupported playlist claims. | Domain map exists. | Closed at docs/domain-contract level. |
| R-FH-P1-019 | Keep side metrics display-only until confidence improves | P1 | CS2 Domain / Metrics | Metrics | Closed | FH-P1-019 / FH-067 | AR-045; Macro-batch B report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-060_069_review.md`. | Side metrics are documented as display-only until confidence improves. | Keep hard side advice blocked until accepted future evidence improves confidence. | Side hard advice is blocked until confidence improves. | Closed for current display-only block. |
| R-FH-P1-020 | Block hard trade recommendations before parser hardening | P1 | CS2 Domain / Metrics | Metrics | Closed | FH-P1-020 / FH-068 | AR-047; Macro-batch B report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-060_069_review.md`. | Hard trade recommendations are explicitly blocked before parser hardening. | Keep hard trade claims forbidden until parser evidence improves under future scope. | Hard trade claims are forbidden. | Closed for current block. |
| R-FH-P1-021 | Keep source limitations visible | P1 | CS2 Domain / Source limits | Metrics / UI | Closed | FH-P1-021 / FH-069 / FH-083 | AR-054; Macro-batch B report; Macro-batch D report; PM reviews `/opt/jc-coach-pm/reviews/2026-07-08_FH-060_069_review.md` and `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md`. | Coach/API/AI contracts require source limitations and evidence chains to remain visible. | Preserve source-limit visibility in future output/UI/API work. | Source limits remain visible. | Closed at docs/contracts level. |
| R-FH-P1-022 | Define sample-size thresholds per metric/category | P1 | CS2 Domain / Metrics | Metrics / QA | Closed | FH-P1-022 / FH-072 / FH-075 through FH-079 | AR-055; TASK-AUDIT-004; Macro-batch C1 report; Macro-batch C2 report and PM review. | Sample-size thresholds and confidence-label fixture coverage exist. | Maintain thresholds and caveats in future metric work. | Thresholds are documented and covered by current golden/confidence fixture checks. | Closed for current docs/tests scope. |
| R-FH-P1-023 | Keep formula/reliability sync tests | P1 | Data / Metrics | Metrics / QA | Closed | FH-P1-023 / FH-076 | AR-068; Macro-batch C2 report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-075_079_review.md`. | Formula/reliability sync regression coverage exists. | Maintain sync tests for accepted metrics. | Sync check passes. | Closed for current sync-test scope. |
| R-FH-P1-024 | Add golden aggregate fixture suite | P1 | Data / Metrics / Tests | Metrics / QA | Closed | FH-P1-024 / FH-077 / FH-097 | AR-069, AR-087; Macro-batch C2 report; Macro-batch E2 report and PM review. | Golden aggregate fixture suite exists and is visible in final readiness/local gate checks. | Maintain fixtures when accepted core metrics change. | Core accepted metrics have golden fixtures. | Closed for current fixture suite. |
| R-FH-P1-025 | Create source trust registry | P1 | Data / Metrics / Import | Metrics / Import | Closed | FH-P1-025 / FH-070 / FH-071 | AR-072; TASK-AUDIT-004; Macro-batch C1 report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-070_074_review.md`. | Source trust registry covers current CSV, JSON, demo, Steam/Valve and FACEIT states. | Maintain trust levels and usage rules in future source changes. | Source trust is referenced by coach policy. | Closed at docs/contracts level. |
| R-FH-P1-026 | Document aggregation rules | P1 | Data / Metrics | Metrics / QA | Closed | FH-P1-026 / FH-073 / FH-077 | AR-073; Macro-batch C1 report; Macro-batch C2 report and PM review. | Aggregation rules are documented and represented by current golden fixtures. | Maintain aggregation rules/fixtures in future metric work. | Aggregation cases are tested or documented for current accepted scope. | Closed for current docs/tests scope. |
| R-FH-P1-027 | Version metric registry/prompt payload snapshots | P1 | Data / AI reproducibility | Metrics / Architect | Accepted risk | FH-P1-027 / FH-086 | AR-076; Macro-batch D report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-080_088_review.md`; FH-125A-01 no-engine schema boundary. | Versioned metric-registry/prompt-payload snapshot plan exists, but runtime snapshots were not generated and schema work remains blocked. | Implement runtime snapshot persistence only under future explicit schema/migration scope. | Accepted no-schema/versioning plan exists for current readiness rerun. | Accepted limitation; future runtime persistence remains gated. |
| R-FH-P1-028 | Add global DB import-order smoke guard | P1 | Runtime / DB | DB / Runtime / QA | Closed | FH-P1-028 / FH-036 | AR-081; FH-036 report and PM review; commit `3a6990a`. | A focused test-only subprocess smoke guard now checks DB/config/model import ordering against temp SQLite DBs. | Maintain the guard and keep production DB dependency out of import-order tests. | Unsafe import order is guarded by the accepted test. | Closed for the import-order smoke-guard scope. This does not close `R-FH-P0-001`; migration-engine/adoption remains hard-blocked as a visible limitation. |
| R-FH-P1-029 | Add CI quality gates | P1 | Tests / CI | TEST_GUARDIAN | Accepted risk | FH-P1-029 / FH-023 / FH-024 / FH-038_039 / FH-096 / FH-097 / FH-124R-01 | AR-090; FH-023 report and commit `25d2eb2`; FH-024 report and commit `a95fb3f`; FH-038/039 local gate rerun evidence; Macro-batch E2 PM review; FH-124R-01 recovery report. | Regressions are checked by an accepted mandatory local CI-equivalent gate; hosted CI is not configured. FH-124R-01 proved current full-suite/local-gate pass evidence after the H1 stall. | Preserve local gate discipline; decide hosted CI/provider setup separately if future policy requires it. | Required checks are standard; local CI-equivalent coverage is accepted for the current personal/restricted lane. | Accepted local-only limitation, not a hosted CI claim. H1 still needs rerun and acceptance before final readiness. |
| R-FH-P1-030 | Keep SHA in every DB-impacting WP | P1 | Ops / DB | DB / PM | Closed | FH-P1-030 / FH-032 / FH-037 | AR-093; FH-032 report and commit `0c37b40`; FH-037 report and commit `65fa1f8`; `AGENTS.md`; `docs/project_management/AGENT_WORKFLOW.md`; `docs/BACKUP_RESTORE.md`. | DB-impact reporting policy now distinguishes ordinary tasks, DB/schema-risk no-touch tasks, read-only production inspection and authorized production DB mutation. | Maintain the policy in future DB-risk Task Cards and reports. | DB-impacting WPs require appropriate no-touch, read-only SHA or mutation before/after SHA evidence. | Closed for policy/reporting coverage. It does not authorize production DB mutation. |
| R-FH-P1-031 | Add secret redaction command policy | P1 | Security / Command safety | Security | Closed | FH-P1-031 / FH-112 | AR-095; Macro-batch G report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-110_117_review.md`; `docs/SECURITY.md`. | Secret redaction command/output policy is documented. | Keep reports/docs limited to secret names/purposes and no values. | Reports forbid secret values. | Closed at docs/governance level. |
| R-FH-P1-032 | Keep public-readiness rate-limit restriction | P1 | Security / Runtime | Security / Runtime | Closed | FH-P1-032 / FH-115 | AR-097; Macro-batch G report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-110_117_review.md`; `docs/SECURITY.md`; `docs/KNOWN_LIMITATIONS.md`. | Current in-memory rate limiting is documented as not public-grade and public-readiness claims remain blocked. | Keep public-readiness blocked until a future explicit public-grade rate-limit/deploy task passes. | Public claims are blocked. | Closed for restriction/documentation scope only; no public-grade limiter was implemented. |
| R-FH-P1-033 | Add data privacy/retention policy before sharing | P1 | Security / Privacy | Security / PM | Closed | FH-P1-033 / FH-114 | AR-098; Macro-batch G report; PM review `/opt/jc-coach-pm/reviews/2026-07-08_FH-110_117_review.md`; `docs/SECURITY.md`. | Privacy/retention requirements are documented before any sharing feature. | Keep sharing/social features blocked until future explicit policy/runtime scope allows them. | Sharing is blocked pending future explicit public/friends scope. | Closed for current docs/governance requirement; no sharing/public feature is authorized. |

## P2/P3 Import Status

P2/P3 items are not imported in FH-010. The current source for those items
remains `03_P2_P3_TRIAGE.md` until a future task explicitly scopes structured
triage import. This keeps FH-010 limited to the P0/P1 backlog required by the
task card.

## Review Notes For PM

- All P0 risks are represented. `R-FH-P0-001` and `R-FH-P0-002` are
  `Hard-blocked` visible limitations; `R-FH-P0-003` is `Closed` for the design
  requirement only. No migration engine, production migration capability,
  public/friends access or runtime planner implementation is claimed.
- All P1 risks from the current backlog are represented. Most P1 risks are
  `Closed` by accepted macro-batch evidence. `R-FH-P1-003`, `R-FH-P1-005`,
  `R-FH-P1-006`, `R-FH-P1-016`, `R-FH-P1-027` and `R-FH-P1-029` remain
  explicit `Accepted risk` boundaries for current readiness-rerun purposes.
- `R-FH-P1-002` is `Closed` because FH-010 created the register, FH-011
  verified P0/P1 field coverage and FH-012 linked it from current
  source-of-truth and roadmap docs.
- Major CS2 feature work remains blocked until `04_READINESS_GATE.md` evaluates
  to PASS.
- Public/friends access, import cap raise, schema-changing product work and
  unsupported coach claims remain visibly blocked.
