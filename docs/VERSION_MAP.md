# Version Map

Last updated: 2026-07-03.

| Version | Name | Status | Evidence | Blockers |
|---|---|---|---|---|
| v0.1 | Personal Dashboard | done | CSV/JSON import, dashboard, matches, analytics, rule report, tests. | None for original MVP. |
| v0.2 | Problem Detection | partial | Rule-based coach report and weakness detection exist. | Confidence model and metric suppression are incomplete. |
| v0.3 | Recommendation Engine | partial | Active recommendations, categories and lifecycle exist. | Needs planner from top verified problem snapshots. |
| v0.4 | Alpha Foundation | current foundation | Есть personal dashboard, imports, parser foundation, rule-based diagnosis, recommendation lifecycle, AI handoff/persistence и Steam alpha path. | Не готово для friends/public; нужны metric truth, parser confidence, recommendation planner и structured AI hardening. |
| v0.5 | Parser/Map/Side Deep Dive | started | Deep parser tables, `swing_score`, match detail parser blocks. | Side switching, KAST/trade, timing, utility and verification need hardening. |
| v0.6 | AI Coach Summary | partial | Handoff, local LLM scaffold and report persistence exist. | Structured output schema, validator and versioned prompts are missing. |
| v0.7-prep | Secure Single/Friends Alpha + Honest Coach Loop | active milestone | Текущий hardening plan описан в `docs/CURRENT_MILESTONE.md`. | Test isolation, backup, Security P0, ownership/single-user mode, Steam cursor truth, Metric Truth Layer, parser hardening, diagnosis/recommendation planner. |
| v0.7 | Secure Friends Alpha | blocked | Login/register and nginx deployment scaffolding exist. | API auth, ownership/single-user mode, CSRF/rate limits, strong secrets, migrations, backup and observability. |
| v0.8 | Production Steam Sync | blocked | Steam alpha import path exists. | Durable worker, retry/backoff, cursor freshness, stale cursor handling. |
| v1.0 | Public Product | not_started | Product direction exists. | Security, multi-user isolation, reliable metrics, support/ops and legal/product readiness. |
