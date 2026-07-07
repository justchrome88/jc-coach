# Known Limitations

Last updated: 2026-07-08.

- Not secure for friends/public use yet.
- `v0.9` Real Data Onboarding is promoted with warnings for controlled
  personal one-demo-capped use only.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1` until a separate cap-change WP.
- Match playlist mode is not accepted as exact in `v0.9`; current data can use
  provenance/limitation labels only, not Premier/Competitive/Wingman/Casual/
  Deathmatch/FACEIT/custom claims.
- CS2 domain boundaries are conservative in `docs/CS2_DOMAIN_CONTRACT.md`:
  economy, positioning and clutch models are unavailable; current map labels
  are source-provided until a canonical map registry is accepted; side metrics
  are display-only; hard trade recommendations are blocked before parser
  hardening; coach output must keep these source limitations visible.
- Authenticated owner-browser timing was not captured by Codex for WP-017H.
- `/coach` artifact overview is acceptable at 22 demos but should be optimized
  before materially larger demo volume.
- Historical queued non-parent Steam jobs `#1` and `#10` remain.
- Metric Truth Layer exists, but some metrics remain approximate/low/unavailable and must stay warning-only or suppressed as defined in `docs/METRICS.md`.
- Steam import is alpha and needs durable worker/retry/freshness hardening.
- AI output validator exists for structured reports, but prompt versioning, provider-specific structured response mode and semantic entailment checks remain future work.
- `/coach` is coach-first over current tracked recommendation, but it is not recommendation planner and does not identify a verified top problem yet.
- 2026-07-06 agentic-readiness audit score is `66%`; major CS2 feature work is
  restricted until the foundation recovery gate passes.
- Migration baseline/schema gate is a foundation blocker before schema features.
- Structured risk register, source trust/sample-size policy, prompt/payload
  versioning, semantic AI evals and API contract/gate enforcement remain
  foundation hardening items.
- Raw `.dem` files are not deleted.
- FACEIT, viewer, heatmaps, clips, payments and social features are deferred.
