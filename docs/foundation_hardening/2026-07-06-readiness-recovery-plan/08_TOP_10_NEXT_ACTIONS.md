# Top 10 Next Actions

Date: 2026-07-06.

Source: audit `10_NEXT_10_TASKS.md` and `09_RECOMMENDED_TASKS.md`.

| Priority | Action | Reason | Expected readiness impact | Owner | Complexity | Dependencies |
|---:|---|---|---|---|---|---|
| 1 | Create migration baseline and schema gate. | Schema is the highest-risk foundation blocker. | Large: removes P0 schema blocker. | DB_GUARDIAN / Execution / QA | L | No production DB mutation; backup/SHA policy. |
| 2 | Add mandatory CI/local quality gate. | Agentic rules can currently be skipped. | Large: turns manual checks into enforced gate. | TEST_GUARDIAN | M | Project gate command standard. |
| 3 | Create structured risk register. | Limitations lack owner/status/target WP. | Medium/large: makes risk closure trackable. | PM / Docs | M | Docs source-of-truth decision. |
| 4 | Define source trust and sample-size policy. | Coach advice can overclaim from weak/small data. | Large: protects metrics/coach truth. | METRICS_GUARDIAN | M/L | Metric Truth docs/tests. |
| 5 | Add prompt/payload versioning. | AI outputs are not reproducible across prompt changes. | Medium/large: improves auditability. | METRICS_GUARDIAN / Execution | M | Migration gate if persistence schema changes. |
| 6 | Build first semantic AI eval suite. | Schema validation cannot prove advice quality. | Large: catches hallucination/overclaim cases. | QA_REVIEWER / Metrics | M | Advice confidence/source policy. |
| 7 | Design diagnosis registry and recommendation planner. | Coach cannot choose a verified top problem yet. | Large: resolves P0 coach blocker. | Architect / METRICS_GUARDIAN | L | Source trust, sample-size, eval contracts. |
| 8 | Expand architecture map and API contracts. | Boundaries and endpoint contracts are too thin. | Medium: safer agent edits. | RUNTIME_GUARDIAN / QA | M | Current route inventory. |
| 9 | Add CS2 domain pack document. | Domain rules are scattered and several models are unavailable. | Medium: prevents unsupported CS2 facts. | DOCUMENTATION_STEWARD / Metrics | M | Source/sample policy. |
| 10 | Plan durable import worker and retry ledger. | Cap raises are unsafe with BackgroundTasks/coarse job truth. | Medium/large: blocks unsafe import scale-up. | IMPORT_GUARDIAN / Architect | L | Migration gate for later implementation. |

