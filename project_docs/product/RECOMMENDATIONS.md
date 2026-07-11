> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/RECOMMENDATIONS.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Recommendations

Last updated: 2026-07-11.

## Current Truth

Recommendation tracking exists: active goals, categories, baseline/target metrics, lifecycle actions and per-match evaluation are implemented.

Stage 4 split read/write behavior: recommendation GET/read helpers read existing recommendations/evaluations only and do not create rows or commit implicitly. Explicit POST/command/import paths remain responsible for mutations.

Stage 5 adds Metric Truth Layer. Recommendation scoring can consume only metrics that are allowed for hard recommendation usage. Warning metrics may appear as context/evidence, but must not become a hard success/failure claim.

Stage 6 keeps parser-derived weak facts out of hard recommendation claims. `early_deaths` may be present only when parser timing anchors exist, and it remains warning-only.

Stage 8 AI Output Validator applies the same Metric Truth constraints to structured AI recommendations: suppressed/unavailable metrics cannot support recommendation claims, and approximate/warn metrics require caveats.

The remaining implementation gap is planning. This document defines the
accepted diagnosis registry and recommendation planner design contract, but no
runtime planner implementation is accepted yet. The system must not create a
new planner-backed primary recommendation until the implementation entry
criteria below pass.

## Canonical Loop

```text
verified problem -> evidence -> primary recommendation -> next matches -> evaluation -> progress/change
```

## Primary Focus And Evidence Contract

The accepted focus rule is one primary active recommendation at a time. The
primary recommendation must come from the top verified problem snapshot that
has hard-usable evidence under `project_docs/metrics/METRICS.md` and accepted CS2 domain
boundaries under `project_docs/product/CS2_DOMAIN_CONTRACT.md`.

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

## Diagnosis Registry Design

The diagnosis registry is a future deterministic registry of verified problem
snapshots. It is a contract before implementation, not a new runtime store in
this task.

A problem snapshot is eligible for the registry only when every required link
is available:

- stable problem id and human-readable label;
- owning recommendation category;
- allowed metric ids with Metric Truth usage decisions;
- source trust tiers for all contributing facts;
- match ids, aggregate windows, sample counts and omitted/missing counts;
- `metric_confidence` for each hard-claim metric;
- evidence confidence after applying metric reliability, source trust, sample
  size, aggregation/window quality and CS2 domain availability;
- caveats for approximate, mixed-source, missing, low-sample or
  source-limited evidence;
- explicit unavailable/suppressed facts that must not be inferred.

The registry may contain only verified problems. A verified problem has enough
accepted evidence to support at least bounded recommendation wording. Low,
suppressed, unavailable, display-only or below-threshold metrics may appear
only as caveated context and must not make a problem verified by themselves.

The registry must preserve this evidence chain:

```text
problem -> metric -> match/window -> recommendation
```

If a future implementation cannot build the full chain for a candidate, it
must keep the candidate out of planner priority selection and may expose it
only as low-confidence context.

## Recommendation Planner Design

The planner is a future deterministic selector that chooses one primary
recommendation from the top verified problem snapshot. It does not replace
Metric Truth, source-trust rules, the AI Output Validator, CS2 domain
boundaries or human review.

Planner responsibilities:

- read eligible problem snapshots from the diagnosis registry;
- reject candidates that lack required evidence links or `metric_confidence`;
- reject candidates whose hard evidence depends on weak, suppressed,
  unavailable, display-only or below-threshold metrics;
- rank verified candidates by evidence confidence, severity/opportunity,
  recency/window quality, actionability and continuity with the current
  accepted primary focus;
- select exactly one primary focus;
- create or update only the recommendation category that directly follows from
  the selected problem;
- carry evidence links, confidence and caveats into recommendation creation,
  evaluation and AI coach payloads;
- leave secondary goals as context only unless a future accepted planner task
  changes the focus model.

The planner must prefer continuity when evidence is close. Replacing the
current primary focus requires a clearly stronger verified problem, a completed
or failed current focus, or explicit user/operator action. Small-sample noise,
warning-only metrics or unsupported CS2 concepts must not churn the primary
focus.

## Allowed Planner Inputs

Future planner implementation may use only these input classes:

- Metric Truth entries and usage decisions from `project_docs/metrics/METRICS.md` and the
  runtime metric registry;
- source trust tiers, aggregation rules, sample-size thresholds and period
  comparison semantics from `project_docs/metrics/METRICS.md`;
- accepted CS2 domain boundaries from `project_docs/product/CS2_DOMAIN_CONTRACT.md`;
- persisted match facts and parser/import artifacts that are already accepted
  for the specific metric and source claim;
- current recommendation state, baseline, target metric ids, evaluation window
  and `metric_confidence`;
- deterministic AI coach payload/result metadata only after prompt/payload and
  metric-registry versions are present and validator constraints pass;
- explicit operator/user actions where the current product flow already
  accepts them.

Future planner implementation must not use:

- live AI/provider calls as a source of truth;
- parser reruns, live Steam/Valve imports, evaluator jobs or manual evaluator
  jobs unless separately authorized by that future task;
- production DB mutation or schema changes unless explicitly scoped with the
  required backup/SHA and schema evidence;
- hidden heuristics that are not represented in the registry contract;
- old audit reports, old task prompts or historical roadmap docs as current
  planner inputs;
- unsupported playlist/mode, map, side, trade, economy, positioning, clutch or
  FACEIT claims.

## Weak-Metric Exclusions

The planner must exclude weak metrics from hard priority selection. Excluded
hard-evidence sources include:

- Metric Truth `low`, `suppressed` or `unavailable` decisions;
- approximate or `warn` metrics used as the sole reason for a diagnosis,
  recommendation, success/failure, progress or replacement decision;
- samples below the threshold for the metric category or comparison window;
- missing `metric_confidence`;
- mixed-source aggregates whose weakest relevant source or metric policy
  prevents hard advice;
- display-only side metrics;
- trade claims beyond validated v3 same-round five-second aggregate counts and
  rates, including any spatial/tactical cause or individual counterfactual;
- unavailable economy, positioning, clutch, crosshair placement, aim-rating,
  grenade-rating or canonical map models;
- exact playlist/mode assumptions for Premier, Competitive, Wingman, Casual,
  Deathmatch, FACEIT or custom when current data only proves provenance.

Weak metrics may still explain why a candidate needs review, why confidence is
low or why no planner recommendation should be created.

## One-Primary-Focus Selection Logic

Future planner selection must be deterministic and auditable:

1. Build candidate problem snapshots from allowed inputs only.
2. Drop candidates that cannot satisfy the evidence chain or hard-evidence
   eligibility rules.
3. Assign candidate confidence as the weakest relevant confidence across
   metric reliability, source trust, sample size, aggregation/window quality
   and CS2 domain availability.
4. Rank only candidates with hard-usable evidence. Ranking may consider
   severity, opportunity size, recency, stability across windows,
   actionability and continuity with the current primary focus.
5. Select exactly one primary problem.
6. Produce exactly one primary recommendation for that problem.
7. Carry all caveats, metric ids, match/window evidence and
   `metric_confidence` into the recommendation and later evaluation.
8. If no candidate passes eligibility, create no new hard recommendation and
   report "no verified primary problem yet" with the limiting reasons.

Tie-breaking must be stable. If two candidates have similar confidence and
impact, keep the current accepted primary focus unless it is complete, stale,
failed or explicitly replaced by the operator.

## Planner Implementation Entry Criteria

Planner implementation remains blocked until all criteria below pass in an
explicit future implementation task:

- this diagnosis registry and planner design contract is accepted;
- Metric Truth/source-trust/sample-size rules and weak-metric exclusions remain
  current;
- advice confidence and evidence-link contracts remain current;
- prompt/payload and metric-registry version contracts are either implemented
  or an accepted no-schema workaround is documented for planner evidence;
- semantic AI eval and golden metric readiness fixtures remain visible in the
  required local gate;
- future task scope names allowed files, DB/schema authorization status,
  required tests/evals and rollback expectations;
- future task proves no production DB mutation, schema change, live
  import/parser/evaluator job, service/deploy change or external AI/provider
  call occurs unless explicitly authorized.

Until those criteria pass, the accepted product behavior is still the existing
recommendation tracking loop. This design does not create planner runtime
behavior, does not authorize a new ProblemSnapshot table or schema artifact,
and does not unlock unrelated product work.

## Progress And Weak-Evidence Wording

Progress language must match evidence strength:

- hard progress wording requires accepted metrics, `metric_confidence`,
  compatible windows and enough samples;
- weak or small-sample evidence may say "early signal", "limited evidence",
  "possible pattern" or "not enough matches yet";
- warning-only metrics may explain context but must not be the sole reason for
  extending, completing, failing or replacing a recommendation;
- unavailable or suppressed metrics must not appear as recommendation evidence.

Unsupported hard advice from weak metrics is blocked. Validated v3 trade
counts/rates may support bounded aggregate `bad_fight_trade` evidence, but side,
economy, positioning, clutch, exact playlist/mode, spatial trade cause and other
unavailable or display-only concepts cannot drive recommendation priority or
evaluation.

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

## Remaining Capability Gaps

- Implement diagnosis registry only after the entry criteria above pass in an
  explicit scoped task.
- Implement top verified problem selection only after the entry criteria above
  pass in an explicit scoped task.
- Implement planner creation of one primary recommendation with evidence and
  confidence only after the entry criteria above pass in an explicit scoped
  task.
- Runtime evidence links from recommendation to matches/metrics/problems.
- Planner integration with Metric Truth Layer.
