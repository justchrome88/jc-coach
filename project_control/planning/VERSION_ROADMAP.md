# Version Roadmap

Last updated: 2026-07-11.

This is the single macro Product roadmap. Detailed planned work belongs in
`WORK_PACKAGE_BACKLOG.md`; exact task status belongs in `WP_REGISTRY.md`.
Historical task-level detail remains in PM reports, Git history, and
`_legacy_archive/`.

## A. Product goal

Build a personal CS2 AI Coach around exactly two canonical coaching domains:
`impact_leak` and `bad_fight_selection`. The Product must use validated
evidence and real LLM hypotheses to offer measurable missions, count progress
only on subsequent matches, and show evidence-based per-match feedback with
confidence and caveats.

## B. Completed milestones

| Milestone | Accepted outcome | Evidence |
|---|---|---|
| Foundation and safety hardening | Readiness, mutation, ownership, test, and operating guardrails accepted. | `_legacy_archive/r02a2-2026-07-11/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md` |
| Import/parser/owner vertical loop | Controlled fresh-match discovery and owner-scoped processing loop accepted. | `/opt/jc-coach-pm/reports/H01A_fresh_match_user_assisted_vertical_cycle_acceptance_report.md` |
| Metric truth and semantic versioning | Canonical metric contracts, registry validation, and production trusted subset accepted. | `/opt/jc-coach-pm/reports/H01A-M03_production_metric_migration_trusted_subset_acceptance_and_h01b_release_decision_report.md` |
| Coach Metric Pack and ten-match acceptance | Coach Metric Pack and replay evidence accepted with caveats. | `/opt/jc-coach-pm/reports/H01A-M04_coach_metric_pack_v1_completion_and_production_acceptance_report.md` |
| Two-domain reconciliation | Exactly two domains and independent domain behavior accepted. | `/opt/jc-coach-pm/reports/H01B-R01_canonical_two_domain_reconciliation_and_ten_match_replay_report.md` |
| Real LLM 30-match hypothesis engine | Immutable 30-match baseline, real structured hypotheses, and two proposal slots accepted. | `/opt/jc-coach-pm/reports/H01B-R02_two_domain_ai_hypothesis_and_mission_proposal_engine_report.md` |
| Documentation/control/runtime-contract consolidation | Canonical zones, current-document parity, and the final two-file compatibility shell accepted. | `/opt/jc-coach-pm/reports/H01B-R02A2D_final_docs_shell_and_roadmap_reconstruction_report.md` |

## C. Completed milestone — R02A3 codebase/service-boundary consolidation

R02A3 makes the accepted backend easier to change safely before UI work. It
consolidates application package and service boundaries without changing
Product behavior, DB/schema/data, domain contracts, or the two-domain model.

Accepted outcome: bounded package ownership, reduced cross-service coupling,
stable public behavior and imports, an updated package-level code map, and all
focused plus full technical gates passing.

## D. Completed inserted acceptance gate — R02A4 full vertical observability

R02A4 is a one-time acceptance gate inserted before UI work. It proves that the
consolidated architecture operates as one complete owner-scoped Steam-to-coach
pipeline using a genuine acquisition, real parser, current metrics, real model
calls for both canonical domains, clone-only dual activation, subsequent-match
progress, stable raw card serialization, and sanitized per-stage lineage.

R02A4 does not add a permanent Product feature or expand domains, metrics,
provider architecture, import capacity, schema, public readiness, or UI scope.
R03 remained gated until this acceptance task closed.

Accepted outcome: external storage expansion allowed the unchanged guard to
pass, then a fresh isolated run proved the complete real vertical chain,
two-domain clone activation, subsequent-match evaluation, two-card backend,
repeat/concurrency/failure behavior, complete sanitized trace, and production
no-mutation. Evidence:
`/opt/jc-coach-pm/reports/H01B-R02A4R_storage_remediated_full_vertical_acceptance_report.md`.
R03 is released.

## E. Functional MVP milestone — R03 minimal functional UI

Deliver complete functionality with minimal styling:

- two domain cards with analyzing, proposal, no-problem, insufficient-data,
  and error states;
- proposal pinning and explicit activation of one, both, or neither;
- at most one active mission per owner and domain, with no automatic activation;
- per-domain mission lifecycle with baseline, current, target, confidence, and
  caveats;
- per-match coaching feedback and progress history that counts only matches
  after activation baseline; and
- authentication and owner isolation across UI and API behavior.

## F. End-to-end acceptance milestone — R04 30+10 replay

Prove the full Product loop with a 30-match immutable baseline, two supported
proposals, explicit activation of both, and 10 subsequent matches fed one by
one. Acceptance requires independent progress timelines, insufficient-data
handling, idempotent reprocessing, and DB/API/dashboard/match-page parity.

## G. Live personal beta milestone — R05 planned, not authorized

Process real newly played personal matches; review hypothesis usefulness,
false positives and unsupported claims, latency and provider reliability, and
mission target quality. Collect Product changes before visual polish.

## H. Visual Product milestone — R06 planned, not authorized

After functional MVP acceptance and personal-match validation, improve
responsive layout, visual hierarchy, loading/empty/error states, mission
history presentation, readable evidence and caveats, accessibility, and design
consistency.

## I. Operational hardening milestone — R07 deferred/planned

Harden provider routing, queues, observability, reliability, and cost controls
after Product validation unless R03–R05 exposes an earlier blocker. This is not
a prerequisite for the personal MVP by default.

## J. Later/public scope

Multi-user/public readiness, public deployment, broader coach domains, and
additional tactical or spatial evidence are later work. They are not current
MVP requirements; no third coach domain is authorized.

Canonical sequence: **R02A4 inserted acceptance gate → R03 → R04 → R05 planned → R06 planned →
R07 deferred/planned**. Working complete functionality precedes replay and real
personal validation; visual polish follows both.
