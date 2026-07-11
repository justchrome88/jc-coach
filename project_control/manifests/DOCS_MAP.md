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
| Compatibility shell | `docs/README.md`, `docs/metrics/AGENTS.md` | Fixed-path agent discovery only; never Product/runtime truth |
| Historical evidence | `_legacy_archive/` and Git history | Noncanonical; never active/runtime input |
| PM reports/artifacts | `/opt/jc-coach-pm/reports/` | Task evidence |

No active runtime reader or writer may use `docs/` or `_legacy_archive/`. The
only active `docs/` consumer is agent-policy discovery of
`docs/metrics/AGENTS.md` as directed by root `AGENTS.md`.
