# Handoff

Last updated: 2026-07-11.

Read, in order:

1. root `AGENTS.md`;
2. `project_control/status/CURRENT_STATUS.md`;
3. this handoff;
4. `project_control/planning/WP_REGISTRY.md`;
5. only task-relevant `project_docs/` or `project_control/` files.

The active task is the no-loss documentation/control/runtime-contract migration
`H01B-R02A2`. Its accepted predecessor is the read-only R02A1 audit at PM
commit `ddd82b33b2ac48b428f491bcb97328ce2e06c6f9`. The required Product ancestor
is `f6497197f1696460572be3b3a33ec104e8ee5a12`.

R02A2 must preserve all 332 original `docs/` files byte-identically, leave no
runtime reader on `docs/`, reconcile PM routing, preserve the production DB and
service process, and commit seven atomic Product batches. Compatibility stubs
are temporary and read-only.

After R02A2, execute R02A3 service-boundary consolidation. R03 mission-card and
activation UI work remains blocked until R02A3 is accepted; R04 replay follows
R03.

Current accepted behavior is summarized in `CURRENT_STATUS.md`. Historical
status blocks and task evidence are noncanonical under `_legacy_archive/` or PM
reports and must not be loaded as active context.
