> R02A2 canonical source: `_legacy_archive/r02a2-2026-07-11/docs/coach/AI_HYPOTHESIS_ENGINE_ARCHITECTURE.md`. The original is preserved byte-identically; this copy updates canonical paths only.

# Two-Domain AI Hypothesis Engine

## Accepted stack

H01B-R02 extends the existing `app.services.ai_coach` provider path. Production is configured as
`codex_cli_handoff`; the installed Codex CLI is authenticated with ChatGPT and the configured model is
`gpt-5.6-sol`. Structured domain calls use the existing configured command with `--ephemeral`, a read-only
sandbox, and `--output-schema`. No second SDK, credential, or provider stack is introduced. The older handoff
and local OpenAI-compatible/Ollama paths remain readable and functional.

Production invocation is `run_domain_analysis` → `invoke_configured_structured_model` → configured Codex CLI.
Tests inject a bounded callable at the same application boundary. The canonical output schema is
`app/contracts/coach/schemas/ai-domain-hypothesis.schema.json`; the CLI constrains syntax, then
`validate_domain_output` independently resolves domains, refs, exact values, metric versions, targets,
claim boundaries, and leakage rules.

## Operational contract

- Timeout: the configured provider timeout (90 seconds by default).
- Attempts: one initial call and one structured repair call. Later operator retries append attempt lineage.
- Failure classes: `provider_timeout`, `provider_error`, `validation_failed`, and malformed output. Failed
  attempts are retained by hash and reason code; they never create proposals.
- Telemetry: provider, configured model, route, request/thread ID when emitted, input/output tokens, latency,
  and response hash. Secrets and unrestricted raw responses are not stored.
- Privacy: the bundle contains owner ID plus a hashed Steam identity, validated aggregates, bounded per-match
  observations, and lineage IDs. Raw event payloads, demos, credentials, prompts containing secrets, and
  provider stderr are excluded from persistence and API output.
- Idempotency: owner + domain + immutable baseline hash + prompt version + evidence version + configured
  provider/model route. An accepted identity is reused; retries are explicit append-only attempts.

## Persistence and application boundary

`coach_evidence_baselines` freezes the exact chronological 30-match set. `ai_domain_analyses` is append-only.
`coach_mission_proposals` has one partial-unique current row per owner/domain. `coach_domain_slots` has exactly
one owner/domain row. Proposals never activate missions. Existing deterministic hypotheses remain readable.
Mission activation now suppresses only the same canonical domain, allowing one active mission per domain.

`GET /api/coach/domains` returns the stable two-slot owner payload. Technical provenance is opt-in; prompts,
raw responses, secrets, and raw events are never serialized.
