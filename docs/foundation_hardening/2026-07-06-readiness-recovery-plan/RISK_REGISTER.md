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
| Status | Current conservative state: `Open`, `Hard-blocked`, `Accepted risk`, `Closed`, `Pending import`, `Superseded` or `Needs clarification`. |
| Target FH task or WP | The hardening task, WP or future task expected to resolve or decide the risk. |
| Source evidence | Source row, document or audit reference that proves the risk exists. |
| Current impact | Why the risk matters now. |
| Required next action | Next concrete action needed to reduce, close or decide the risk. |
| Acceptance / exit condition | Evidence required before the risk can leave `Open`. |
| Notes | Constraints, dependencies, visible blocked work or reporting notes. |

## Status Policy

- No risk is marked `Closed` unless source evidence already proves closure.
- No risk is marked `Accepted risk` unless an explicit acceptance source exists.
- P0 risks must be closed or explicitly hard-blocked before the readiness gate
  can pass.
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
| Import cap raise / larger Steam demo batches | Blocked until worker/retry/schema safety is accepted. | `00_EXECUTIVE_DECISION.md`; FH-P1-009. | `R-FH-P1-007`, `R-FH-P1-009`, `R-FH-P0-001`. |
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
| Status | Open |
| Target FH task or WP | FH-P0-001 |
| Source evidence | `02_P0_P1_HARDENING_BACKLOG.md` FH-P0-001; audit matrix AR-019, AR-026, AR-067; audit `08_CRITICAL_GAPS.md`; `09_RECOMMENDED_TASKS.md` TASK-AUDIT-001. |
| Current impact | Schema evolution relies on startup create/upgrade behavior. Future schema work could silently drift or mutate `data/cs2_coach.db` outside a controlled migration process. |
| Required next action | Adopt Alembic or equivalent baseline, schema diff policy and production apply approval/SHA policy on a DB copy first. |
| Acceptance / exit condition | Baseline matches current schema on a copy; production DB is untouched; startup helper receives no new schema changes; schema-changing WPs require explicit migration scope; task report includes checks and DB safety evidence. |
| Notes | Major schema-changing product work remains blocked until this risk is closed or explicitly hard-blocked. |

### R-FH-P0-002 - Keep Public/Friends Access Blocked Until Security Gate

| Field | Value |
|---|---|
| Risk ID | R-FH-P0-002 |
| Title | Personal-only app could be treated as shareable before security/privacy readiness. |
| Criticality | P0 |
| Layer / category | Web Application Core / Security / Privacy / Ops |
| Owner role | Security / PM / QA |
| Status | Open |
| Target FH task or WP | FH-P0-002 |
| Source evidence | `02_P0_P1_HARDENING_BACKLOG.md` FH-P0-002; audit matrix AR-027; audit `07_AGENTIC_WORKFLOW_OPS_SECURITY.md`; audit `00_EXECUTIVE_SUMMARY.md`. |
| Current impact | Controlled personal/VPS use is acceptable, but access expansion lacks completed privacy, observability, rate-limit, deployment and owner-boundary guarantees. |
| Required next action | Keep explicit release-gate language blocking public/friends work until security/privacy/ops criteria pass. |
| Acceptance / exit condition | Public/friends work is visibly blocked in current status, roadmap pause/resume and readiness gate; no product access expansion occurs. |
| Notes | Public/friends access, social sharing and public-readiness claims remain blocked. |

### R-FH-P0-003 - Design Diagnosis Registry And Recommendation Planner

| Field | Value |
|---|---|
| Risk ID | R-FH-P0-003 |
| Title | Coach may produce plausible advice without verified problem selection. |
| Criticality | P0 |
| Layer / category | AI Coach Product Archetype / Recommendation planning |
| Owner role | Architect / Metrics Guardian / Execution / QA |
| Status | Open |
| Target FH task or WP | FH-P0-003 |
| Source evidence | `02_P0_P1_HARDENING_BACKLOG.md` FH-P0-003; audit matrix AR-033; audit `08_CRITICAL_GAPS.md`; `09_RECOMMENDED_TASKS.md` TASK-AUDIT-007. |
| Current impact | The coach tracks recommendations but does not yet choose a primary recommendation from verified problems, which makes major coach-quality expansion unsafe. |
| Required next action | Design allowed inputs, confidence policy, one primary focus rule, weak-metric exclusions and evidence links before implementation. |
| Acceptance / exit condition | Planner design is accepted and implementation entry criteria are explicit; implementation remains gated until metric/source/eval contracts are ready. |
| Notes | Major planner implementation and unsupported coach/domain claims remain blocked. |

## P1 Risks

All P1 risks from `02_P0_P1_HARDENING_BACKLOG.md` are represented below. None
are marked closed or accepted by FH-010.

| Risk ID | Title | Criticality | Layer / category | Owner role | Status | Target FH task or WP | Source evidence | Current impact | Required next action | Acceptance / exit condition | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R-FH-P1-001 | Expand project gate pre/postflight | P1 | Agentic Core / Tests | TEST_GUARDIAN / Execution | Open | FH-P1-001 | AR-009; `06_TESTS_EVALS_QUALITY.md`; TASK-AUDIT-002 | Checks can be skipped or reported inconsistently. | Add explicit status, changed-file, required-check and postflight workflow. | Reports require gate output and local gate passes. | Supports later CI/local enforcement. |
| R-FH-P1-002 | Create structured risk register | P1 | Agentic Core / Risk tracking | PM / Docs | Closed | FH-P1-002 / FH-010 / FH-012 | AR-015; `03_DOCS_AND_CONTEXT.md`; TASK-AUDIT-003; FH-010 report; FH-011 report; FH-012 report. | Risks now have owner/status/target WP/evidence in one canonical register linked from current docs. | Maintain the register links and update future risk status only through scoped task evidence. | Register is linked from current docs and accepted by PM review. | FH-010 created the artifact, FH-011 verified P0/P1 field coverage and FH-012 linked it from `CURRENT_STATUS.md`, `WP_REGISTRY.md`, `VERSION_ROADMAP.md` and `WORK_PACKAGE_BACKLOG.md`. |
| R-FH-P1-003 | Add automated enforcement of agent rules | P1 | Agentic Core / CI | TEST_GUARDIAN / QA | Open | FH-P1-003 | AR-016; `07_AGENTIC_WORKFLOW_OPS_SECURITY.md` | Manual rules can be bypassed. | Add CI or mandatory local equivalent. | Failure blocks PASS claims. | Depends on FH-P1-001. |
| R-FH-P1-004 | Expand architecture map | P1 | Web Core / Architecture | Architect / Runtime | Open | FH-P1-004 | AR-017; `04_ARCHITECTURE_CODEBASE.md` | Agents may mutate the wrong layer because boundaries are thin. | Document module, data-flow and mutation boundaries. | Boundaries are inspectable in architecture docs. | Docs-first unless a future task scopes code/tests. |
| R-FH-P1-005 | Add API contract inventory/tests | P1 | Web Core / API contracts | Runtime / QA | Open | FH-P1-005 | AR-018; TASK-AUDIT-008 | Endpoint behavior can drift without contract tests. | Inventory core endpoints and add critical read/mutation contract tests. | Core contracts are tested. | Depends on FH-P1-004. |
| R-FH-P1-006 | Harden owner/auth edge state | P1 | Web Core / Security | Security / Runtime | Open | FH-P1-006 | AR-020; `07_AGENTIC_WORKFLOW_OPS_SECURITY.md` | Single-owner assumptions remain fragile in edge config states. | Add owner state/config docs and tests or accepted limitation. | Edge cases are tested or explicitly accepted. | No public/friends access work. |
| R-FH-P1-007 | Create job error taxonomy and result_json schema | P1 | Web Core / Import | Import Guardian | Open | FH-P1-007 | AR-022, AR-029; TASK-AUDIT-010 | Import outcomes can be ambiguous because coarse status hides detail. | Document outcome taxonomy and `result_json` schema. | Outcomes have schema and examples. | Related to import cap safety. |
| R-FH-P1-008 | Create safe env reference | P1 | Web Core / Ops / Security | Security / Docs | Open | FH-P1-008 | AR-025 | Required/optional env vars are not fully documented safely. | Document env variable names and purposes without values. | Safe reference exists and reveals no secret values. | Reports must not print secret values. |
| R-FH-P1-009 | Plan durable worker/retry ledger before cap raise | P1 | Web Core / Ops / Import | Import / Architect | Open | FH-P1-009 | AR-029; TASK-AUDIT-010 | BackgroundTasks are fragile for larger Steam/import behavior. | Design worker, retry ledger and staged DB requirements. | Cap raise remains blocked until design is accepted. | Depends on FH-P1-007 and later FH-P0-001 for implementation. |
| R-FH-P1-010 | Create generic AI coach archetype model doc | P1 | AI Coach / Architecture | Architect / Metrics | Open | FH-P1-010 | AR-031 | Coach-core concepts are tangled with CS2 domain assumptions. | Define coach-core concepts independent of CS2 domain pack. | Separation is documented. | Docs-only unless future implementation is scoped. |
| R-FH-P1-011 | Enforce one primary accepted focus until planner exists | P1 | AI Coach / PM | Metrics / PM | Open | FH-P1-011 | AR-032 | Multiple goals could be misread as accepted hard focus. | Document and enforce one primary accepted focus until planner passes. | One-focus rule is explicit. | Depends on FH-P0-003. |
| R-FH-P1-012 | Calibrate progress wording and sample confidence | P1 | AI Coach / Metrics / UI | Metrics / UI / QA | Open | FH-P1-012 | AR-034 | Small-sample progress can be overstated. | Calibrate wording and caveats for current recommendation progress. | Wording matches confidence and sample size. | Source trust policy needed. |
| R-FH-P1-013 | Keep metric_confidence mandatory | P1 | AI Coach / Metrics | Metrics / QA | Open | FH-P1-013 | AR-035 | Weak evidence can become hard result if confidence is missing. | Add contract/check that evaluations include `metric_confidence`. | Missing confidence fails. | Must preserve current recommendation rule. |
| R-FH-P1-014 | Create coach advice confidence contract | P1 | AI Coach / Metrics | Metrics / Architect | Open | FH-P1-014 | AR-036 | Advice-level confidence is not formally defined. | Define advice confidence from source, sample, metric reliability and caveats. | Advice confidence contract is accepted. | Depends on source trust risk R-FH-P1-025. |
| R-FH-P1-015 | Add evidence link model | P1 | AI Coach / Explainability | Metrics / Architect | Open | FH-P1-015 | AR-037 | Problem-to-recommendation explainability is incomplete. | Define problem -> metric -> match -> recommendation evidence chain. | Chain is required for hard advice. | Depends on R-FH-P1-014. |
| R-FH-P1-016 | Add prompt/payload versioning | P1 | AI Coach / Reproducibility | Metrics / Execution / QA | Open | FH-P1-016 | AR-038; TASK-AUDIT-005 | AI outputs are not reproducible across prompt/payload changes. | Add versions to metadata/persistence or document no-schema workaround first. | Versions are visible in result metadata or accepted workaround exists. | Schema changes depend on R-FH-P0-001. |
| R-FH-P1-017 | Build semantic AI eval suite | P1 | AI Coach / Tests | QA / Metrics | Open | FH-P1-017 | AR-039, AR-088; TASK-AUDIT-006 | Schema validation cannot prove advice entailment or quality. | Add golden eval fixtures for supported and unsupported claims. | Eval suite blocks overclaim cases. | Depends on R-FH-P1-014. |
| R-FH-P1-018 | Add CS2 match/round domain map | P1 | CS2 Domain / Docs | Docs / Metrics | Open | FH-P1-018 | AR-043; TASK-AUDIT-009 | Domain facts are scattered. | Document match/round/sides/map/source facts and limits. | Domain map exists. | Must not add unsupported playlist claims. |
| R-FH-P1-019 | Keep side metrics display-only until confidence improves | P1 | CS2 Domain / Metrics | Metrics | Open | FH-P1-019 | AR-045 | CT/T side metrics are not ready for hard advice. | Document display-only status and parser confidence requirement. | Side hard advice is blocked until confidence improves. | Depends on source/sample policy. |
| R-FH-P1-020 | Block hard trade recommendations before parser hardening | P1 | CS2 Domain / Metrics | Metrics | Open | FH-P1-020 | AR-047 | Trade logic is weak for hard recommendations. | Explicitly block hard trade claims until parser evidence improves. | Hard trade claims are forbidden. | Unsupported trade coach claims remain blocked. |
| R-FH-P1-021 | Keep source limitations visible | P1 | CS2 Domain / Source limits | Metrics / UI | Open | FH-P1-021 | AR-054 | Source limits can be hidden from coach output. | Add source limitation contract for UI/coach output. | Source limits remain visible. | Depends on source trust risk R-FH-P1-025. |
| R-FH-P1-022 | Define sample-size thresholds per metric/category | P1 | CS2 Domain / Metrics | Metrics / QA | Open | FH-P1-022 | AR-055; TASK-AUDIT-004 | Small samples can drive overconfident advice. | Define thresholds and caveats per metric/category. | Thresholds are enforced or documented. | Related to source trust risk R-FH-P1-025. |
| R-FH-P1-023 | Keep formula/reliability sync tests | P1 | Data / Metrics | Metrics / QA | Open | FH-P1-023 | AR-068 | Formula docs and code can drift. | Maintain or extend sync tests for accepted metrics. | Sync check passes. | Protects metric truth. |
| R-FH-P1-024 | Add golden aggregate fixture suite | P1 | Data / Metrics / Tests | Metrics / QA | Open | FH-P1-024 | AR-069, AR-087 | Aggregate regressions may be missed. | Add fixtures for accepted core metrics. | Core accepted metrics have golden fixtures. | Depends on R-FH-P1-022. |
| R-FH-P1-025 | Create source trust registry | P1 | Data / Metrics / Import | Metrics / Import | Open | FH-P1-025 | AR-072; TASK-AUDIT-004 | Weak sources can drive hard advice. | Define trust levels and usage rules for CSV, JSON, demo, Steam/Valve and FACEIT states. | Source trust is referenced by coach policy. | Key dependency for confidence/caveat risks. |
| R-FH-P1-026 | Document aggregation rules | P1 | Data / Metrics | Metrics / QA | Open | FH-P1-026 | AR-073 | Aggregation semantics are incomplete. | Document rules and add representative fixtures. | Aggregation cases are tested. | Depends on R-FH-P1-024. |
| R-FH-P1-027 | Version metric registry/prompt payload snapshots | P1 | Data / AI reproducibility | Metrics / Architect | Open | FH-P1-027 | AR-076 | Old AI outputs may not be reproducible. | Version metric registry and payload snapshots. | Versioned snapshots exist. | Depends on R-FH-P1-016. |
| R-FH-P1-028 | Add global DB import-order smoke guard | P1 | Runtime / DB | DB / Runtime / QA | Open | FH-P1-028 | AR-081 | Careless scripts can hit production DB through global engine/settings hazards. | Reduce global binding or add import-order smoke tests. | Unsafe import order is guarded. | Depends on R-FH-P0-001. |
| R-FH-P1-029 | Add CI quality gates | P1 | Tests / CI | TEST_GUARDIAN | Open | FH-P1-029 | AR-090 | Regressions can land unchecked without CI or equivalent. | Add CI or accepted mandatory local substitute. | Required checks are standard. | Depends on R-FH-P1-003. |
| R-FH-P1-030 | Keep SHA in every DB-impacting WP | P1 | Ops / DB | DB / PM | Open | FH-P1-030 | AR-093 | DB impact can become unclear without SHA discipline. | Include DB SHA requirement in gate/report template. | Report template requires SHA for DB-impacting WPs. | Depends on R-FH-P1-001. |
| R-FH-P1-031 | Add secret redaction command policy | P1 | Security / Command safety | Security | Open | FH-P1-031 | AR-095 | Command output can leak sensitive values if policy is vague. | Document allowed command reporting: names only, no values. | Reports forbid secret values. | No secret values should appear in task outputs. |
| R-FH-P1-032 | Keep public-readiness rate-limit restriction | P1 | Security / Runtime | Security / Runtime | Open | FH-P1-032 | AR-097 | In-memory rate limiting is not public-grade. | Document no public readiness and later reverse-proxy/Redis limiter need. | Public claims are blocked. | Depends on R-FH-P0-002. |
| R-FH-P1-033 | Add data privacy/retention policy before sharing | P1 | Security / Privacy | Security / PM | Open | FH-P1-033 | AR-098 | Sensitive data exposure risk remains before sharing/social features. | Define privacy/retention policy before any sharing feature. | Sharing is blocked pending policy. | Depends on R-FH-P0-002. |

## P2/P3 Import Status

P2/P3 items are not imported in FH-010. The current source for those items
remains `03_P2_P3_TRIAGE.md` until a future task explicitly scopes structured
triage import. This keeps FH-010 limited to the P0/P1 backlog required by the
task card.

## Review Notes For PM

- All P0 risks are represented and remain `Open`.
- All P1 risks from the current backlog are represented. `R-FH-P1-002` is
  `Closed` after FH-010/FH-011/FH-012 evidence; remaining P1 risks remain
  `Open`.
- `R-FH-P1-002` is `Closed` because FH-010 created the register, FH-011
  verified P0/P1 field coverage and FH-012 linked it from current
  source-of-truth and roadmap docs.
- Major CS2 feature work remains blocked until `04_READINESS_GATE.md` evaluates
  to PASS.
- Public/friends access, import cap raise, schema-changing product work and
  unsupported coach claims remain visibly blocked.
