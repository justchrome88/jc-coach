> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/metrics/contracts/temporal_survival.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Temporal Survival Contract

Semantic supplement `3.1.0` derives survival time only from accepted completed round boundaries, proven owner
participation/side lineage, and an accepted owner death inside that round. A survived round ends at the accepted
round end. A death ends at its accepted tick. The implementation uses the parser contract of 64 ticks/second.

Not-participating rounds, incomplete rounds, and rounds containing a disconnect are excluded. Reconnect is
recorded but does not make the interrupted round complete. Warmup and post-round/post-match deaths are excluded.
Regulation and overtime remain explicitly labeled. Combat activity is never used to infer presence or time alive.

The per-round ledger is persisted as provenance. Seven scalar aggregates are registered as trusted performance
metrics: average/median/p25 survival time, early-death rate before 45 seconds, average death time, and T/CT-side
average death time. Existing validated `3.0.0` snapshots are preserved.
