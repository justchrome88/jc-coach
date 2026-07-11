# AI Output Validation Inventory

Дата: 2026-07-03.

Stage: 8 — AI Output Validator.

## Verdict

Stage 8 можно выполнить без schema changes и live AI calls.

Существующие поля достаточны для MVP validator:

- AI input payload строится в `app/services/ai_coach.py::build_ai_coach_payload`;
- provider/handoff boundary находится в `AIProvider`, `CodexCliHandoffProvider`, `LocalLLMProvider`;
- AI result сохраняется в `coach_reports.report_markdown`;
- metadata/payload snapshot сохраняются в `coach_reports.report_json`;
- Stage 8 validation metadata can be stored inside existing `report_json`.

Separate structured AI output table is not required for this stage.

## AI Output Surfaces

| Surface | File/function | Current behavior | Stage 8 action |
|---|---|---|---|
| Payload builder | `app/services/ai_coach.py::build_ai_coach_payload` | Builds deterministic facts, metric truth, recommendations and recent matches. | Keep as input source. |
| Prompt builder | `app/services/ai_coach.py::build_ai_coach_prompt` | Instructed Russian Markdown report. | Updated to request strict JSON schema and caveats. |
| Handoff provider | `CodexCliHandoffProvider.prepare` | Writes payload/prompt/result placeholder files. | No live AI call; prompt now asks for structured JSON. |
| Local provider | `LocalLLMProvider.generate` | Calls configured local/Ollama/OpenAI-compatible endpoint. | No provider rewrite; validator runs after output is returned. |
| Save pasted/generated result | `save_ai_coach_result` | Previously accepted non-empty free-form Markdown. | Now validates structured output; invalid output becomes safe fallback Markdown. |
| API save route | `POST /api/coach/ai/result` | Calls `save_ai_coach_result`. | Inherits validator. |
| Web save route | `/coach/ai-result` | Calls `save_ai_coach_result`. | Inherits validator. |
| Report serialization | `serialize_ai_coach_report` | Returns markdown and metadata. | Exposes `metadata.ai_validation` from existing `report_json`. |

## Metric Truth Inputs

Stage 5 already adds `metric_truth` to AI payload:

- selected metric definitions;
- `suppressed_for_diagnosis`;
- `suppressed_for_recommendation`.

Stage 8 validator uses runtime Metric Truth Layer directly:

- unknown id -> reject;
- suppressed/unavailable id -> reject for diagnosis/recommendation;
- warn/approximate id -> require caveat.

## Validation Policy

Accepted top-level schema:

```text
summary
diagnoses[]
recommendations[]
warnings[]
evidence[]
confidence
```

Diagnosis item must include:

```text
category
claim
evidence_metric_ids[]
confidence
caveats[]
```

Recommendation item must include:

```text
category
action
rationale
target_metric_ids[]
confidence
caveats[]
```

Rejected:

- missing required sections;
- invalid confidence value;
- unknown metric id;
- suppressed/unavailable metric used as diagnosis/recommendation evidence;
- approximate/warn metric without caveat;
- invalid/free-form/non-JSON provider output.

## Unsupported Claim Risks After Stage 8

- Provider-specific structured response enforcement is not implemented. The prompt requests JSON, but the validator is the enforcement point.
- Prompt/version tracking is not implemented.
- Validator checks metric ids and caveats, not semantic truth of every sentence.
- Recommendation planner and ProblemSnapshot are still future work, so AI recommendations are guarded but not planner-derived.
- Existing old AI reports in DB are not backfilled or revalidated.

## No-Run Guarantees During Stage 8

- No live AI provider calls are required for implementation/tests.
- No production Steam/import/parser jobs are required.
- No production DB mutation is required.
- No DB schema changes are required.
