# AI Coach

Last updated: 2026-07-03.

## Current Truth

The default provider is `codex_cli_handoff`. The application creates deterministic payloads and prompt files for human-in-the-loop Codex analysis.

`local_llm` exists as a scaffold for Ollama, LM Studio or OpenAI-compatible local servers. AI result persistence exists.

Stage 5 payloads include `metric_truth`: selected metric definitions plus metrics suppressed for diagnosis/recommendation. This is metadata only; AI output is still free-form and not schema-validated.

Stage 6 parser payloads add clearer warnings for early-death timing, KAST trade component, traded deaths, side stats and utility/flash confidence. AI must treat those warnings as constraints, not as coachable facts by themselves.

## Rules

- AI consumes structured facts; it does not parse demos.
- AI must not invent missing statistics.
- AI output must state low confidence when source data is weak.
- AI must not turn `suppressed` Metric Truth entries into confident diagnosis or recommendations.
- AI must present `warn` metrics as approximate/contextual, not as fully trusted facts.
- AI recommendations are subordinate to verified metrics and the recommendation planner.

## Gaps

- Free-form Markdown output is not enough for product automation.
- Structured output schema is needed.
- Validator is needed.
- Prompt and payload version tracking must be explicit.
- Validator must reject unsupported metric claims after schema work exists.

## Next Work

Create schema-validated AI output with fields for diagnosis, evidence, recommendation, confidence, warnings and next-match evaluation plan.
