# Instructions Audit Report

Audit date: 2026-07-03.

## Summary

The documentation set had no single hierarchy. README, worklog, roadmap files, audit files, prompt libraries and `instructions/*` all contained a mix of current truth, historical plans and future ideas.

This pass establishes `docs/PROJECT_CONTROL.md` as the canonical source of truth and splits the audit into:

- `docs/audit/INSTRUCTIONS_INVENTORY.md`
- `docs/audit/DOCUMENT_CONFLICTS.md`
- `docs/audit/DOCUMENT_DEPRECATION_PLAN.md`

## Main Findings

- Product version labels lag reality: `v0.1` appears in user-facing docs while the codebase has a broader personal-alpha foundation.
- Security readiness was easy to overread because login/deployment docs exist, but the audit shows friends/public readiness is still blocked.
- Metric docs mixed desired future metrics with reliable current metrics.
- Recommendation docs described lifecycle well but did not enforce the current primary-recommendation-from-verified-problem direction.
- Steam docs needed a canonical alpha/current truth around OpenID, Game Authentication Code, latest share-code cursor and service bot resolver.
- AI docs needed to reflect that persistence exists but structured output validation is still missing.
- Old prompt libraries can conflict with current user constraints by requesting jobs, commits, pushes or broad feature work.

## Result

Canonical docs were added/updated, stale docs were marked historical, and no old documents were deleted.

