# Work-Package Registry

Last updated: 2026-07-11.

This is the concise authoritative status registry. Detailed scope belongs in
`WORK_PACKAGE_BACKLOG.md`; the human milestone view belongs in
`../checklists/MASTER_WP_CHECKLIST.md`.

- CURRENT_TASK: `H01B-R02A4T_TRUE_TIMED_OBSERVABILITY_PROVENANCE_AND_TWO_CARD_SEMANTIC_CLOSURE`
- NEXT_TASK: `H01B-R03_TWO_MISSION_CARDS_ACTIVATION_AND_MATCH_FEEDBACK_UI`
- NEXT_TASK_GATED: `true`
- CANONICAL_SEQUENCE: `R02A4R accepted → R02A4T timed evidence closure → R03 → R04 → R05 planned → R06 planned → R07 deferred/planned`

| Task/milestone | Status | Gate / dependency | Evidence |
|---|---|---|---|
| Foundation and safety hardening | completed | none | `_legacy_archive/r02a2-2026-07-11/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/04_READINESS_GATE.md` |
| Import/parser/owner loop | completed | foundation | `/opt/jc-coach-pm/reports/H01A_fresh_match_user_assisted_vertical_cycle_acceptance_report.md` |
| Metric correctness and Coach Metric Pack | completed | owner loop | `/opt/jc-coach-pm/reports/H01A-M04_coach_metric_pack_v1_completion_and_production_acceptance_report.md` |
| H01B-R01 two-domain backend | complete_with_warnings | metrics | `/opt/jc-coach-pm/reports/H01B-R01_canonical_two_domain_reconciliation_and_ten_match_replay_report.md` |
| H01B-R02 real LLM proposals | complete_with_warnings | R01 | `/opt/jc-coach-pm/reports/H01B-R02_two_domain_ai_hypothesis_and_mission_proposal_engine_report.md` |
| H01B-R02A2D | complete_with_warnings | R02A2C | `/opt/jc-coach-pm/reports/H01B-R02A2D_final_docs_shell_and_roadmap_reconstruction_report.md` |
| H01B-R02A3 | complete_with_warnings | R02A2D | `/opt/jc-coach-pm/reports/H01B-R02A3_codebase_service_boundary_consolidation_report.md` |
| H01B-R02A4 | complete_with_warnings | accepted by storage-remediated R02A4R continuation; first blocked evidence preserved | `/opt/jc-coach-pm/reports/H01B-R02A4R_storage_remediated_full_vertical_acceptance_report.md` |
| H01B-R02A4T | current | clone-only timed observability, source provenance, and semantic closure; no external rerun | add accepted R02A4T report |
| H01B-R03 | next_gated | temporarily gated by R02A4T evidence closure | add accepted R03 report |
| H01B-R04 | pending | requires accepted R03 | add accepted R04 report |
| H01B-R05 | planned | requires accepted R04 and live-action authority | none |
| H01B-R06 | planned | follows Product validation, including R05 findings | none |
| H01B-R07 | deferred_planned | follows validation unless an earlier blocker proves need | none |
| WP-018 and old foundation task rows | historical_superseded | not active route | archived source and Git history |

Task IDs must not be reused. An explicit current task card controls immediate
scope. Deferred, failed, historical, or superseded work must never be reported
as implemented.

Historical R02A4 blocker evidence includes
`/opt/jc-coach-pm/reports/H01B-R02A4_full_vertical_acceptance_artifact.json`
and `/opt/jc-coach-pm/reports/H01B-R02A4_stage_trace.jsonl`. Accepted continuation
evidence is indexed in the R02A4 row; R03 is released.
