# JC Coach Control Plane

This is the canonical root for current Product control state.

- `status/`: current status and handoff.
- `planning/`: current route, roadmap, and backlog.
- `checklists/`: current acceptance and release gates.
- `agents/`: supporting agent policies, roles, and guardians.
- `manifests/`: active routing and documentation maps.

Authority order is defined by root `AGENTS.md`. Compatibility files under
`docs/` are read-only pointers and must never be writer targets.
