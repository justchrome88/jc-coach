# Recommendations

Last updated: 2026-07-03.

## Current Truth

Recommendation tracking exists: active goals, categories, baseline/target metrics, lifecycle actions and per-match evaluation are implemented.

The remaining product gap is planning. The system must choose one primary active recommendation from the top verified problem snapshot instead of diluting focus across loosely related category goals.

## Canonical Loop

```text
verified problem -> evidence -> primary recommendation -> next matches -> evaluation -> progress/change
```

## Rules

- Do not create a primary recommendation from unreliable metrics.
- Keep secondary category goals only when they support the main focus.
- Preserve the baseline used to create a goal.
- Separate read-only recommendation summaries from write/evaluation side effects.
- Show why a match was green/yellow/red against the active recommendation.

## Next Work

- Diagnosis registry.
- Top verified problem selection.
- Planner that creates one primary recommendation with evidence and confidence.
- Evidence links from recommendation to matches/metrics/problems.

