# Recommendations

Last updated: 2026-07-08.

## Current Truth

Recommendation tracking exists: active goals, categories, baseline/target metrics, lifecycle actions and per-match evaluation are implemented.

Stage 4 split read/write behavior: recommendation GET/read helpers read existing recommendations/evaluations only and do not create rows or commit implicitly. Explicit POST/command/import paths remain responsible for mutations.

Stage 5 adds Metric Truth Layer. Recommendation scoring can consume only metrics that are allowed for hard recommendation usage. Warning metrics may appear as context/evidence, but must not become a hard success/failure claim.

Stage 6 keeps parser-derived weak facts out of hard recommendation claims. `early_deaths` may be present only when parser timing anchors exist, and it remains warning-only.

Stage 8 AI Output Validator applies the same Metric Truth constraints to structured AI recommendations: suppressed/unavailable metrics cannot support recommendation claims, and approximate/warn metrics require caveats.

The remaining product gap is planning. The system must choose one primary active recommendation from the top verified problem snapshot instead of diluting focus across loosely related category goals.

## Canonical Loop

```text
verified problem -> evidence -> primary recommendation -> next matches -> evaluation -> progress/change
```

## Primary Focus And Evidence Contract

The accepted focus rule is one primary active recommendation at a time. The
primary recommendation must come from the top verified problem snapshot that
has hard-usable evidence under `docs/METRICS.md` and accepted CS2 domain
boundaries under `docs/CS2_DOMAIN_CONTRACT.md`.

Secondary goals may exist only as supporting context for the primary focus.
They must not compete with the primary recommendation, create separate hard
progress claims or dilute the evaluation window unless a future planner task
explicitly accepts that behavior.

Every primary recommendation and every hard evaluation must preserve the
evidence link model:

```text
problem -> metric -> match -> recommendation
```

Required evidence fields at contract level:

- problem id or problem label;
- metric ids and Metric Truth usage decisions;
- match ids, aggregate windows or sample counts behind the metrics;
- recommendation id and active evaluation window;
- `metric_confidence` for recommendation/evaluation evidence where applicable;
- caveats for weak, approximate, mixed-source, missing or low-sample evidence.

`metric_confidence` remains mandatory anywhere recommendation creation,
evaluation or AI coach advice uses metric evidence for a hard claim. Missing
`metric_confidence` means the evidence can be displayed as context only and
must not create a hard success, failure, priority or progress claim.

## Progress And Weak-Evidence Wording

Progress language must match evidence strength:

- hard progress wording requires accepted metrics, `metric_confidence`,
  compatible windows and enough samples;
- weak or small-sample evidence may say "early signal", "limited evidence",
  "possible pattern" or "not enough matches yet";
- warning-only metrics may explain context but must not be the sole reason for
  extending, completing, failing or replacing a recommendation;
- unavailable or suppressed metrics must not appear as recommendation evidence.

Unsupported hard advice from weak metrics is blocked. Trade, side, economy,
positioning, clutch, exact playlist/mode and other unavailable or display-only
concepts cannot drive recommendation priority or evaluation until future
parser/source/domain work explicitly upgrades them.

## Rules

- Do not create a primary recommendation from unreliable metrics.
- Do not use `low` or `unavailable` metrics for hard recommendation decisions.
- Use `approximate` metrics only with warning semantics unless a later parser-confidence stage upgrades them.
- AI-generated recommendation output must pass validator checks before it is accepted as confident coach advice.
- Keep exactly one primary active focus unless a future accepted planner task
  changes the focus model.
- Require `metric_confidence` for hard recommendation and evaluation evidence.
- Preserve evidence links from problem to metric to match/window to
  recommendation.
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
- Runtime evidence links from recommendation to matches/metrics/problems.
- Planner integration with Metric Truth Layer.
