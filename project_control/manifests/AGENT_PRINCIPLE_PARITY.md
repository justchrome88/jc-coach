# Agent Principle Parity

R02A1 authority:
`/opt/jc-coach-pm/reports/H01B-R02A1_source_of_truth_inventory.json`.
All listed originals are preserved by the R02A2 migration manifest.

| Principle | Old source | New canonical source | Disposition |
|---|---|---|---|
| branch/worktree | task; Product/PM `AGENTS.md`; project gate | root `AGENTS.md`; PM `AGENTS.md`; `scripts/project_gate.py` | Equivalent or stricter: both repos clean on required branch; unexplained dirt blocks. |
| no push | task; Product/PM `AGENTS.md` | root `AGENTS.md`; PM `AGENTS.md` | Equivalent: no push without explicit request. |
| commit policy | root/PM `AGENTS.md`; old workflow | root `AGENTS.md`; `project_control/agents/AGENT_WORKFLOW.md`; PM `AGENTS.md` | Stricter and mode-aware: manual task authority vs autonomous runner protocol; task wins. |
| production mutation authorization | task; root `AGENTS.md` | root `AGENTS.md`; guardian files | Equivalent: explicit risk scope required for DB/data/import/parser/evaluator/model/Steam/service mutation. |
| backup/restore | `docs/BACKUP_RESTORE.md`; root safety | `project_docs/operations/BACKUP_RESTORE.md`; root `AGENTS.md`; DB guardian | Equivalent: authorized risky work requires scoped backup/SHA/rollback evidence. |
| source priority | root/PM `AGENTS.md` | root `AGENTS.md`; PM `AGENTS.md` | Stricter single nine-level order; archive and PM are subordinate. |
| artifact/report paths | task; PM `AGENTS.md`; old workflow | explicit task; PM `AGENTS.md`; merged PM role | Equivalent: named PM artifacts and task-scoped outputs only. |
| status/checklist update | old workflow/protocol; PM `AGENTS.md` | `project_control/agents/AGENT_WORKFLOW.md`; `PROJECT_OPERATING_PROTOCOL.md`; PM `AGENTS.md` | Equivalent: update canonical Product/PM route set together. |
| current/next routing | Product Hot; PM state/indexes | `project_control/status/*`; `project_control/planning/WP_REGISTRY.md`; PM fixed files/indexes | Stricter: R02A2 → R02A3 → R03 → R04 everywhere. |
| quality gates | root `AGENTS.md`; `docs/TESTING.md`; project gate | root `AGENTS.md`; `project_docs/operations/TESTING.md`; project gate; QA role | Equivalent or stricter: focused plus full applicable gates and no-mutation proof. |
| token economy | root `AGENTS.md`; workflow | root `AGENTS.md`; canonical workflow/roles | Equivalent: smallest relevant context; block broad unclear expansion. |
| stop/block conditions | task; Product/PM `AGENTS.md`; old roles | root/PM `AGENTS.md`; canonical workflow/roles/guardians | Stricter: authority, dirt, mutation, evidence, writer, path, and gate failures block. |
| historical evidence preservation | task; root `AGENTS.md` | root `AGENTS.md`; `_legacy_archive/README.md`; migration manifest | Stricter: byte-identical archive, inactive for runtime/agents, user approval before deletion. |

Parity result: `PASS` when the migration validator confirms all 13 rows and all
recorded old sources are preserved byte-identically.
