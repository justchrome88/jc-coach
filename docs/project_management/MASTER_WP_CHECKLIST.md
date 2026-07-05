# Master WP Checklist

Last updated: 2026-07-05.

This checklist is a human-readable planning map for the full WP campaign.
`docs/project_management/WP_REGISTRY.md` remains canonical for status,
dependencies and report paths. If this checklist and the registry conflict, the
registry wins until the checklist is reconciled.

This file is not per-task Hot context. Use it as Warm context for planning or
audit, and treat it as Cold for ordinary execution.

```text
WP-011D → закрываем навигацию по документации
WP-012 → закрываем DB/test contamination
WP-013 → закрываем runtime smoke gate
WP-014 → проверяем импорт
WP-014A — Import Product Definition + Current State Diagnosis
WP-014B — One-button Steam/Valve Import Repair
WP-014B1 — Import Job Truth + Status Taxonomy
WP-014B2 — Exact Match Date Truth
WP-014B3 — Demo Lifecycle / Cleanup (замена на WP-014B3: Demo Retention Policy and File/DB Consistency, боевое удаление только в коммерции)
WP-014C — One-button Live Acceptance Attempts
WP-014C1 — FAIL: disk/stale running job
WP-014C2 — FAIL: temp storage preflight
WP-014C3 — FAIL: parser/model compatibility
WP-014C4 — PASS_WITH_WARNINGS
WP-014D — Import Acceptance
WP-014D1 repair
WP-014D2 — Steam Import Parent Checkpoints and Interrupted Job Handling
WP-014D3 — Explicit Operator Repair for Stale Steam Import Job #15
WP-014E — Parser Import Match Model Compatibility Repair
WP-014F — Promote Import Acceptance to v0.6
WP-015A — Match Date Truth Reconciliation
WP-015A1 — Controlled Date Truth Backfill / Repair
WP-015 → Metrics Correctness
WP-015B — Metrics Inventory Diagnosis
WP-015C — Metrics Contract / Truth Rules
WP-015C1 — Metrics Performance Repair
WP-015D — Metrics Repair + Tests
WP-015E — Runtime Metrics Acceptance
WP-015F — Promote Metrics Correctness to v0.7
WP-016 → проверяем recommendation loop
WP-016A — Recommendation Loop Acceptance — Diagnosis
WP-016B — Recommendation Loop Legacy Refresh Repair
WP-016C — Controlled Recommendation Refresh
WP-016D — Recommendation Loop Runtime Acceptance
WP-016E — Controlled Next-Match Evaluation Acceptance
WP-016E2 — Controlled Next-Match Evaluation Acceptance
WP-016E3 — Controlled Next-Match Evaluation After Real Competitive Match
WP-016E4 — Post-Import Recommendation Evaluation Repair
WP-016F — promote to v0.8
WP-017 → AI coach acceptance / Real Data Onboarding line
WP-017A — Real Data Onboarding / Bulk Demo Usage Diagnosis
WP-017B — Controlled Bulk Import Plan / Guard Settings
WP-017C — First Controlled Bulk Import Batch / No-New Path
WP-017C2 — Controlled Import After New Match / One-Demo Batch-Cap Path
WP-017D — Post-Batch Acceptance + Auto-Evaluation Trigger Diagnosis
WP-017E — Auto-Evaluation Trigger Repair for Batch-Cap Import Path, if required
WP-017F — Controlled Pending Share Code #73 Import
WP-017G — Post-Batch Data Integrity Acceptance
WP-017H — Post-Batch Performance Acceptance
WP-017I0 — Add Root AGENTS.md Project Contract
WP-017R — Roadmap / WP Registry Governance Repair
WP-017I — Match Mode Classification Diagnosis
WP-017J — Match Mode Classification Repair / Labels, if recoverable
WP-017S — Documentation Governance Entrypoint Repair
WP-017T — Compact Current Status and Handoff
WP-017U — Project Operating Protocol and Master WP Checklist
WP-017K — Real Data Onboarding Promotion to v0.9
WP-018 → Personal MVP release gate / Coach Quality Calibration
WP-018A — Coach Output Quality Diagnosis
WP-018B — Recommendation Category Quality Review
WP-018C — Survival Recommendation Calibration
WP-018D — Aim Recommendation Calibration
WP-018E — Utility / Grenade Recommendation Calibration
WP-018F — Map-Specific Recommendation Calibration
WP-018G — Weak Metric Claim Suppression Review
WP-018H — Coach Explanation / Actionability Repair
WP-018I — 5–10 Match Real Usage Acceptance
WP-018J — Promote Coach Quality Calibration to v0.10
WP-019 → Personal Daily Use UX / v0.11
WP-019A — Daily Use UX Diagnosis
WP-019B — Home / Dashboard “What To Do Now” Repair
WP-019C — Current Recommendation UX Repair
WP-019D — Import Status / Pending Matches UX Repair
WP-019E — Match Review UX Repair
WP-019F — Progress / History UX Repair
WP-019G — Manual Controls: Refresh / Replace / Ignore Recommendation
WP-019H — Empty / Warning / Low-Confidence States
WP-019I — Personal Daily Use Runtime Acceptance
WP-019J — Promote Personal Daily Use UX to v0.11
WP-020 → Deployment / Backup / Storage Hardening / v0.12
WP-020A — Deployment / Storage Diagnosis
WP-020B — Backup Strategy Repair
WP-020C — Restore Drill Acceptance
WP-020D — Demo Retention / Storage Policy Repair
WP-020E — Uploads / TMP / Backups Capacity Guard
WP-020F — Service Reboot / Autostart Acceptance
WP-020G — Log Rotation / Health / Observability Repair
WP-020H — VPS Migration Plan, if needed
WP-020I — Production-Like Runtime Acceptance
WP-020J — Promote Hardening to v0.12
WP-021 → Personal MVP Release Gate / v1.0
WP-021A — Personal MVP Criteria Diagnosis
WP-021B — End-to-End Fresh Match Flow Acceptance
WP-021C — End-to-End Bulk Data Flow Acceptance
WP-021D — End-to-End Coach Recommendation Flow Acceptance
WP-021E — Metrics / Confidence / Known Limitations Review
WP-021F — Backup / Restore / Reboot Final Gate
WP-021G — Performance Final Gate
WP-021H — Personal Usage Trial: 1–2 Weeks
WP-021I — Final MVP Bugfix Batch
WP-021J — Promote Personal MVP to v1.0
```
