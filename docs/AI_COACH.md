# AI Coach

Last updated: 2026-07-08.

## Current Truth

The default provider is `codex_cli_handoff`. The application creates deterministic payloads and prompt files for human-in-the-loop Codex analysis.

`local_llm` exists as a scaffold for Ollama, LM Studio or OpenAI-compatible local servers. AI result persistence exists.

Stage 5 payloads include `metric_truth`: selected metric definitions plus metrics suppressed for diagnosis/recommendation.

Stage 6 parser payloads add clearer warnings for early-death timing, KAST trade component, traded deaths, side stats and utility/flash confidence. AI must treat those warnings as constraints, not as coachable facts by themselves.

Stage 8 adds AI Output Validator without schema changes and without live AI calls. Structured AI output is validated before persistence/display; invalid or free-form output is replaced by safe fallback Markdown and validation metadata is stored in `coach_reports.report_json`.

CS2 domain boundaries are defined in `docs/CS2_DOMAIN_CONTRACT.md`. AI coach
payloads and results must keep those source limitations visible: playlist/mode
is not exact in `v0.9`, economy/positioning/clutch models are unavailable, side
metrics are display-only, current map labels are source-provided and hard trade
recommendations are blocked before parser hardening.

Source trust, mixed-source aggregation, sample-size thresholds and period
comparison semantics are defined in `docs/METRICS.md`. AI coach output must not
turn mixed, missing, low-sample, low-trust or suppressed metrics into hard
diagnosis or recommendations.

## AI Coach Contract

The accepted generic AI coach archetype is an evidence-bound analyst and
wording assistant. It may summarize verified facts, explain caveats, propose
questions for review and format coach output. It is not an authority over the
metric registry, recommendation planner, parser, source-trust policy or CS2
domain boundaries.

Accepted AI coach advice must obey this chain:

```text
problem -> metric -> match -> recommendation
```

Every confident diagnosis or recommendation must be traceable through that
chain:

- `problem`: the verified weakness or opportunity being discussed.
- `metric`: accepted metric ids and Metric Truth usage decisions behind the
  claim.
- `match`: match ids, windows or aggregate sample coverage behind the metric.
- `recommendation`: the active or proposed recommendation that follows from
  the evidence.

If any link is missing, weak, suppressed, unavailable, low-sample or only
approximate, AI output must either avoid hard advice or label the advice as
low-confidence context. It must not fill missing links with inference.

## Advice Confidence Contract

Advice confidence is the minimum supported confidence across metric
reliability, source trust, sample size, aggregation/window quality and CS2
domain availability. AI output may not upgrade the weakest link in the evidence
chain.

| Confidence | Allowed meaning | Required behavior |
|---|---|---|
| `high` | All supporting facts are accepted for the claim, sample thresholds pass and no material caveat changes the advice. | May use direct action wording, but still cite evidence. |
| `medium` | Core evidence is usable, but a limitation such as parser/source coverage, mixed sources or moderate sample size affects certainty. | Use bounded action wording and visible caveats. |
| `low` | Evidence is weak, approximate, sparse, source-limited or exploratory. | Use review/context wording only; do not present as hard advice or success/failure. |

Progress wording must stay calibrated:

- strong wording such as "you improved", "this is working" or "the main issue
  is" requires accepted samples, compatible windows and hard-usable metrics;
- small-sample or mixed-source evidence should say "early signal",
  "limited evidence", "possible pattern" or "needs more matches";
- weak metrics may describe context but must not produce hard progress,
  failure or priority claims.

Unsupported hard advice from weak metrics is blocked. This includes hard
advice from `warn`, `low`, `suppressed` or `unavailable` metrics; unavailable
economy, positioning or clutch models; display-only side metrics; weak trade
semantics; exact playlist/mode assumptions; and samples below the thresholds
defined in `docs/METRICS.md`.

## Versioning And Snapshot Contract

Any AI coach payload, prompt or persisted AI result used for accepted confident
advice must identify the contract versions that shaped it:

- `ai_coach_prompt_version`: the prompt/instruction contract used to ask for
  output.
- `ai_coach_payload_schema_version`: the payload schema/field contract supplied
  to AI.
- `metric_registry_version`: the Metric Truth registry version or snapshot
  identifier used to classify included and suppressed metrics.
- `snapshot_generated_by`: the runtime component that generated the snapshot.
- `snapshot_contract_version`: the metadata contract version for the snapshot.

Runtime payloads include these fields in `contract_snapshot`. Persisted AI
coach reports copy the same fields into `coach_reports.report_json` metadata
and keep the full `payload_snapshot` in that existing flexible JSON field. No
DB schema change is required.

The current snapshot preserves the prompt version, payload schema version,
Metric Truth registry version, included metric definitions,
suppressed/unavailable metric ids, confidence/window metadata, evidence links
available in the payload and the full prompt payload used for the report.

## Rules

- AI consumes structured facts; it does not parse demos.
- AI must not invent missing statistics.
- AI output must state low confidence when source data is weak.
- AI must not turn `suppressed` Metric Truth entries into confident diagnosis or recommendations.
- AI must present `warn` metrics as approximate/contextual, not as fully trusted facts.
- AI recommendations are subordinate to verified metrics and the recommendation planner.
- AI must not infer economy, positioning, clutch, exact playlist/mode,
  canonical map identity or reliable trade semantics from adjacent metrics.
- AI must respect source trust and period comparison boundaries from
  `docs/METRICS.md`: insufficient samples, incompatible source mixes, missing
  values and approximate date sources require caveats or suppression.
- AI output must follow the Stage 8 schema: `summary`, `diagnoses[]`, `recommendations[]`, `warnings[]`, `evidence[]`, `confidence`.
- Accepted confident advice must preserve the evidence chain
  `problem -> metric -> match -> recommendation`.
- `ai_coach_prompt_version`, `ai_coach_payload_schema_version` and the
  metric-registry snapshot/version must be present before future AI advice can
  be treated as accepted versioned evidence.
- Unknown metric ids are rejected.
- Suppressed or unavailable metrics cannot support diagnosis/recommendation claims.
- Approximate/warn metrics require explicit `caveats`.

## Output Schema

Accepted structured output:

```text
summary: string
diagnoses[]:
  category: string
  severity: string
  claim: string
  evidence_metric_ids[]: string
  confidence: low | medium | high
  caveats[]: string
recommendations[]:
  category: string
  action: string
  rationale: string
  target_metric_ids[]: string
  confidence: low | medium | high
  caveats[]: string
warnings[]: string
evidence[]:
  metric_id: string
  value: optional
  caveats[]: string
confidence: low | medium | high
```

Free-form Markdown is no longer accepted as confident coach advice. It is stored only as validator fallback content that says the AI output was rejected.

## Gaps

- Provider-specific structured response enforcement is still shallow; current prompt asks for JSON, and validator rejects invalid output after generation/paste.
- Validation metadata is stored inside existing `coach_reports.report_json`; there is no separate structured AI output table.

## Next Work

- Runtime CS2 domain-constraint block in the AI coach payload.
- Richer provider-specific structured response mode.
- Recommendation planner integration after verified problem snapshots exist.
