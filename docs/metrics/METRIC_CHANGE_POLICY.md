# Metric Change Policy

## Add

Add a registry entry, domain rule, independent fixture, implementation, persistence/selection rules, UI/coach decision, and generated catalog update. Default truth state is `unknown` or `partially_verified`, never `verified` from self-referential tests.

## Change

If include/exclude rules, numerator, denominator, identity, rounding before persistence, or source semantics change, increment `semantic_version`. Preserve old snapshots and record whether a new version needs a new persistence key/column. In-place upsert under the same `(match_id, player_key, source)` is forbidden for changed semantics.

## Deprecate

Set `status=deprecated`, keep the old definition and version, list replacements and consumers, block new hard use, and retain historical evidence.

## Backfill and rollback

A change proposal must name affected snapshots and downstream objects, source evidence availability, idempotency key, quarantine behavior, backfill range, and rollback. Backfill creates version-distinguishable observations; rollback restores consumer selection/quarantine, not rewritten history.

Required checks are registry/schema validation, catalog reproducibility, independent acceptance fixtures, owner/match/player/version selection tests, UI mapping tests, coach-consumption tests, and `git diff --check`.
