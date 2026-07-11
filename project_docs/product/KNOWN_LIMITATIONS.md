> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/KNOWN_LIMITATIONS.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Known Limitations

Last updated: 2026-07-11.

- Not secure for friends/public use yet; public/friends access remains blocked
  until the explicit gate in `project_docs/operations/SECURITY.md` and deploy verification in
  `project_docs/operations/DEPLOYMENT.md` pass in a future authorized task.
- `v0.9` Real Data Onboarding is promoted with warnings for controlled
  personal one-demo-capped use only.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` until a separate cap-change WP.
- Match playlist mode is not accepted as exact in `v0.9`; current data can use
  provenance/limitation labels only, not Premier/Competitive/Wingman/Casual/
  Deathmatch/FACEIT/custom claims.
- CS2 domain boundaries are conservative in `project_docs/product/CS2_DOMAIN_CONTRACT.md`:
  economy, positioning and clutch models are unavailable; current map labels
  are source-provided until a canonical map registry is accepted; side metrics
  are display-only. Bounded aggregate same-round five-second trade
  opportunities and traded/untraded death rates are accepted as context, but
  they do not establish
  exact position, spacing, angle, rotation, crosshair placement or individual
  counterfactual trade instructions.
- Metric Truth Layer exists, but some metrics remain approximate/low/unavailable and must stay warning-only or suppressed as defined in `project_docs/metrics/METRICS.md`.
- Steam import is accepted with warnings for controlled personal one-demo-capped
  use; durable worker/retry/freshness operations and public readiness remain
  incomplete.
- R02 implements versioned prompts/contracts, strict structured output,
  metric/match/value semantic validation, accepted/rejected attempt lineage and
  provider/model provenance. The wider generic report path, durable queue,
  provider operations, observability and cost controls remain incomplete.
- `/coach` is coach-first over current tracked recommendation, but it is not recommendation planner and does not identify a verified top problem yet.
- Current rate limiting is in-memory and not public-grade; privacy/retention,
  incident/log taxonomy and safe environment-reference policies are documented
  but not accepted as public operations readiness.
- Raw `.dem` files are not deleted.
- FACEIT, viewer, heatmaps, clips, payments and social features are deferred.
