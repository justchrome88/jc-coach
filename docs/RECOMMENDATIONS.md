# Recommendations

Last updated: 2026-07-03.

## Current Truth

Recommendation tracking exists: active goals, categories, baseline/target metrics, lifecycle actions and per-match evaluation are implemented.

Stage 4 split read/write behavior: recommendation GET/read helpers read existing recommendations/evaluations only and do not create rows or commit implicitly. Explicit POST/command/import paths remain responsible for mutations.

Stage 5 adds Metric Truth Layer. Recommendation scoring can consume only metrics that are allowed for hard recommendation usage. Warning metrics may appear as context/evidence, but must not become a hard success/failure claim.

Stage 6 keeps parser-derived weak facts out of hard recommendation claims. `early_deaths` may be present only when parser timing anchors exist, and it remains warning-only.

The remaining product gap is planning. The system must choose one primary active recommendation from the top verified problem snapshot instead of diluting focus across loosely related category goals.

## Canonical Loop

```text
verified problem -> evidence -> primary recommendation -> next matches -> evaluation -> progress/change
```

## Rules

- Do not create a primary recommendation from unreliable metrics.
- Do not use `low` or `unavailable` metrics for hard recommendation decisions.
- Use `approximate` metrics only with warning semantics unless a later parser-confidence stage upgrades them.
- Keep secondary category goals only when they support the main focus.
- Preserve the baseline used to create a goal.
- Separate read-only recommendation summaries from write/evaluation side effects.
- GET/read paths must not create recommendations/evaluations or commit.
- Recommendation initialization/evaluation must happen through explicit command paths.
- Show why a match was green/yellow/red against the active recommendation.

## Next Work

- Diagnosis registry.
- Top verified problem selection.
- Planner that creates one primary recommendation with evidence and confidence.
- Evidence links from recommendation to matches/metrics/problems.
- Planner integration with Metric Truth Layer.
