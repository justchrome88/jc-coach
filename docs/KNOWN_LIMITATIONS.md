# Known Limitations

Last updated: 2026-07-03.

- Not secure for friends/public use yet.
- Metric Truth Layer exists, but some metrics remain approximate/low/unavailable and must stay warning-only or suppressed as defined in `docs/METRICS.md`.
- Steam import is alpha and needs durable worker/retry/freshness hardening.
- AI output validator exists for structured reports, but prompt versioning, provider-specific structured response mode and semantic entailment checks remain future work.
- `/coach` is coach-first over current tracked recommendation, but it is not recommendation planner and does not identify a verified top problem yet.
- Raw `.dem` files are not deleted.
- FACEIT, viewer, heatmaps, clips, payments and social features are deferred.
