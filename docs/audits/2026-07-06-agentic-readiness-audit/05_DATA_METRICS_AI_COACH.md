# Data Metrics And AI Coach

## Findings

- Metric Truth Layer is the best-developed quality control in the product domain: stable IDs, formulas, reliability and usage decisions exist in docs and code.
- AI Output Validator blocks unknown/suppressed/unavailable metrics and requires caveats for warning metrics.
- Recommendation tracking has persisted baselines, targets, evaluation rows and progress.
- Current accepted recommendation is survival recommendation `#5`; legacy recommendations must not get new hard evaluations unless refreshed.
- Match mode remains explicitly unknown/provenance-only for v0.9; playlist-specific claims are forbidden.

## Gaps

- No diagnosis registry or top verified problem selector.
- No recommendation planner that creates one primary recommendation from verified evidence.
- Prompt/payload versioning is explicitly listed as future work.
- Semantic AI evals are absent; schema validation is necessary but not sufficient.
- Economy, positioning, traded death rate, crosshair placement and some clutch semantics are not accepted hard evidence.
- Sample-size/source-trust policies need to be unified across metrics.

## Evidence

- `docs/METRICS.md`
- `docs/RECOMMENDATIONS.md`
- `docs/AI_COACH.md`
- `app/services/metric_truth.py`
- `app/services/metric_confidence.py`
- `app/services/recommendation_tracking.py`
- `app/services/ai_validator.py`
- `tests/test_metric_truth.py`
- `tests/test_ai_validator.py`
- `tests/test_recommendation_tracking.py`
- `evidence/metrics_inventory.txt`
