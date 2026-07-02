# AI Coach

Last updated: 2026-07-03.

## Current Truth

The default provider is `codex_cli_handoff`. The application creates deterministic payloads and prompt files for human-in-the-loop Codex analysis.

`local_llm` exists as a scaffold for Ollama, LM Studio or OpenAI-compatible local servers. AI result persistence exists.

## Rules

- AI consumes structured facts; it does not parse demos.
- AI must not invent missing statistics.
- AI output must state low confidence when source data is weak.
- AI recommendations are subordinate to verified metrics and the recommendation planner.

## Gaps

- Free-form Markdown output is not enough for product automation.
- Structured output schema is needed.
- Validator is needed.
- Prompt and payload version tracking must be explicit.

## Next Work

Create schema-validated AI output with fields for diagnosis, evidence, recommendation, confidence, warnings and next-match evaluation plan.

