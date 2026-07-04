# Metrics Guardian

## Scope

Protects Metric Truth, recommendation evidence, diagnosis confidence and AI output truth. Future AI-specific governance may split into `AI_GUARDIAN`; until then AI validator and `ai_coach` truth rules live here.

## Activation Paths

- `app/services/metric_truth.py`
- metrics docs/tests
- recommendation evidence docs/tests
- `app/services/ai_coach.py`
- AI validator code/tests/docs
- recommendation planner/evidence code

## Forbidden Actions

- Presenting weak/best-effort metrics as reliable facts.
- Using unavailable/suppressed metrics for hard diagnosis or recommendation claims.
- Running live AI calls unless explicitly authorized.
- Adding planner or ProblemSnapshot behavior during governance/tooling work.

## Required Checks

- Metric Truth targeted tests when metric behavior changes.
- AI validator tests when AI validation behavior changes.
- Recommendation read/write tests when recommendation evidence paths change.
- Full safe tests when shared behavior changes.
- `git diff --check`.

## Evidence Required

- Metric reliability/usage policy impact.
- Whether AI calls were live or mocked.
- Whether recommendation claims are backed by allowed metrics.
- Tests run and result.

## Escalation / Blocker Rules

Escalate if requested output would overclaim confidence, bypass Metric Truth or rely on unavailable parser facts.

