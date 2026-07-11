# Canonical Documentation Map

Original source preserved at
`_legacy_archive/r02a2-2026-07-11/docs/project_management/DOCS_MAP.md`.

| Concern | Canonical path | Context |
|---|---|---|
| Safety authority | `AGENTS.md` | Hot, always |
| Current status | `project_control/status/CURRENT_STATUS.md` | Hot |
| Handoff | `project_control/status/HANDOFF.md` | Hot for new sessions |
| Current route | `project_control/planning/WP_REGISTRY.md` | Hot |
| Planning/checklists | `project_control/planning/`, `project_control/checklists/` | Task-relevant |
| Agent policies/roles | `project_control/agents/` | Task-relevant |
| Human product docs | `project_docs/README.md` and indexed subdirectories | Task-relevant |
| Coach runtime contracts | `app/contracts/coach/` | Runtime/tool input |
| Metric runtime contracts | `app/contracts/metrics/` | Runtime/tool input |
| DB schema baseline | `app/contracts/db/current_schema_baseline.json` | Read-only gate input |
| Compatibility shell | `docs/` six-file allowlist | Temporary pointers only; never write |
| Historical evidence | `_legacy_archive/` and Git history | Noncanonical; never active/runtime input |
| PM reports/artifacts | `/opt/jc-coach-pm/reports/` | Task evidence |

No active runtime or agent reader may load from `docs/` compatibility stubs or
`_legacy_archive/`.
