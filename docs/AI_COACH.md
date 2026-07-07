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

## Rules

- AI consumes structured facts; it does not parse demos.
- AI must not invent missing statistics.
- AI output must state low confidence when source data is weak.
- AI must not turn `suppressed` Metric Truth entries into confident diagnosis or recommendations.
- AI must present `warn` metrics as approximate/contextual, not as fully trusted facts.
- AI recommendations are subordinate to verified metrics and the recommendation planner.
- AI must not infer economy, positioning, clutch, exact playlist/mode,
  canonical map identity or reliable trade semantics from adjacent metrics.
- AI output must follow the Stage 8 schema: `summary`, `diagnoses[]`, `recommendations[]`, `warnings[]`, `evidence[]`, `confidence`.
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

- Prompt and payload version tracking must be explicit.
- Provider-specific structured response enforcement is still shallow; current prompt asks for JSON, and validator rejects invalid output after generation/paste.
- Validation metadata is stored inside existing `coach_reports.report_json`; there is no separate structured AI output table.

## Next Work

- Prompt and payload version tracking.
- Richer provider-specific structured response mode.
- Recommendation planner integration after verified problem snapshots exist.
