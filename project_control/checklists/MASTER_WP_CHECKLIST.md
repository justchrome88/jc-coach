# Master Work-Package Checklist

Last updated: 2026-07-12. Exact status and gating are authoritative in
`../planning/WP_REGISTRY.md`.

| Product block | Status | Product-facing exit criteria |
|---|---|---|
| Foundation/safety | completed | Safe defaults, mutation controls, ownership, recovery, and local gates accepted. |
| Import/parser/owner loop | completed | A controlled fresh match reaches owner-scoped coaching through validated parser evidence. |
| Metric correctness | completed | Versioned metric truth, lineage, registry/catalog parity, and Coach Metric Pack evidence accepted. |
| Two-domain backend | completed | Exactly `impact_leak` and `bad_fight_selection` exist with independent owner/domain slots. |
| Real LLM proposals | completed | Immutable 30-match baseline and one validated real-LLM proposal per supported domain accepted. |
| Documentation/control migration | completed | Canonical zones are unambiguous; final `docs/` shell has no runtime or Product truth. |
| Codebase architecture cleanup | completed_with_warnings | R02A3 yielded bounded service/package ownership with behavior and full gates preserved. |
| Post-refactor vertical acceptance | completed_with_warnings | R02A4R proved one genuine, observable, isolated Steam-to-coach chain with production unchanged. |
| Timed observability/provenance closure | completed_with_warnings | R02A4T proved a 29-stage clone-only timed replay, explicit source-date provenance, and distinct two-card semantics. |
| Functional mission UI | completed_with_warnings | R03 exposes two complete domain flows, explicit one/both/neither activation, owner isolation, and per-match progress with minimal styling. |
| 30+10 replay | current | R04 proves two proposals and two activated missions across 10 subsequent matches with independent, idempotent DB/API/UI timelines. |
| Live personal beta | pending_gated | Manual user-led R05 evaluates real new-match usefulness, unsupported claims, latency/reliability, and target quality after R04 acceptance. |
| Visual polish | planned | R06 makes the validated flow responsive, accessible, readable, and visually consistent. |
| Provider/ops hardening | deferred_planned | R07 adds measured provider/queue/observability/cost controls after validation unless needed to remove an earlier blocker. |
| Public/multi-user work | later | Separate authorization establishes isolation, deployment, operations, and readiness beyond the personal MVP. |

## MVP acceptance invariants

- [x] Exactly two coach domains; no third domain is planned for the MVP.
- [x] Functional MVP precedes 30+10 acceptance, live personal validation, and
  visual polish.
- [x] R02A4: one isolated genuine Steam-to-coach chain passes with complete
  sanitized stage lineage and production no-mutation proof.
  The first storage-blocked evidence remains preserved; R02A4R passed after
  external capacity remediation without weakening the guard.
- [x] R02A4T: R02A4R remains the live functional proof; the v1 JSONL is a
  terminal summary, while the separate v2 clone replay has 29/29 real timed
  boundaries, explicit date provenance, and distinct card semantics.
- [x] R03: an eligible owner can activate one, both, or neither proposal; never
  automatic activation; at most one active mission per owner and domain.
- [ ] R04 (current): progress uses only matches after activation baseline and preserves
  evidence, confidence, caveats, insufficient-data behavior, and idempotency.
- [ ] R05: real personal-match findings are captured before R06 polish.
