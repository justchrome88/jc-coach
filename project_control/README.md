# JC Coach Control Plane

This is the canonical root for current Product control state.

- `status/`: current status and handoff.
- `planning/`: current route, roadmap, and backlog.
- `checklists/`: current acceptance and release gates.
- `agents/`: supporting agent policies, roles, and guardians.
- `manifests/`: active routing and documentation maps.

Authority order is defined by root `AGENTS.md`. Compatibility files under
`docs/` are read-only pointers and must never be writer targets.

The current safety, evidence-gate, versioning, and task-routing principles from
the former `docs/PROJECT_CONTROL.md` and `docs/PROJECT_GOVERNANCE.md` are
consolidated in root `AGENTS.md` and this control plane. Their complete originals
are preserved in `_legacy_archive/r02a2-2026-07-11/docs/`; stale v0.8/WP-017
status and obsolete commit policy were not carried forward.
