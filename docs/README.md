# Documentation Compatibility Root

`docs/` remains only because repository agent discovery still uses the fixed
path `docs/metrics/AGENTS.md` for metric work. It is not a source of Product,
planning, or runtime truth.

- Human documentation: `project_docs/`
- Runtime contracts, schemas, and registries: `app/contracts/`
- Status, planning, checklists, and agent policy: `project_control/`
- Preserved noncanonical history: `_legacy_archive/`

DO NOT WRITE CURRENT FACTS HERE. Remove this compatibility root only after the
root agent contract no longer routes metric work through the nested entrypoint.
