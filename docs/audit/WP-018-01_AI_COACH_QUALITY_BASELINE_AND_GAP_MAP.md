# WP-018-01 AI Coach Quality Baseline And Gap Map

Task ID: `WP-018-01_AI_COACH_QUALITY_BASELINE_AND_GAP_MAP`

Date: 2026-07-09

## Result

`PASS_WITH_WARNINGS`

The current AI coach quality baseline is documented, the main quality gaps are
ranked, and one first implementation task is recommended. No product code,
tests, DB/schema/data/import/parser/evaluator/runtime/deploy/package files or
prompt runtime behavior were changed.

Warnings remain because WP-018 quality work cannot yet treat AI output as
accepted calibrated evidence: prompt/payload versions and metric-registry
snapshots are missing at runtime, semantic entailment checks are fixture-only,
and the current prompt/payload do not carry a complete explicit CS2 domain
constraint block.

## Branch / HEAD

- Branch: `cona`
- HEAD: `cef52518ed55d94de6e6fee4dc8c28654baf4328`
- Initial `git status --short`: clean, no output.

## Inputs Read

Hot docs:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/project_management/PROMPT_PLAYBOOK.md`
- `docs/audit/PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK_REPORT.md`

Task-relevant Warm docs:

- `docs/AI_COACH.md`
- `docs/RECOMMENDATIONS.md`
- `docs/METRICS.md`
- `docs/CS2_DOMAIN_CONTRACT.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/TESTING.md`

## Code/test Paths Inspected

- `app/services/ai_coach.py`
- `app/services/ai_validator.py`
- `app/services/metric_truth.py`
- `app/services/metric_confidence.py`
- `app/services/recommendation_tracking.py`
- `app/services/coach_rules.py`
- `app/web/routes.py`
- `app/templates/coach.html`
- `tests/test_ai_validator.py`
- `tests/test_ai_coach.py`
- `tests/test_coach_first_ui.py`
- `tests/test_semantic_ai_eval.py`
- `tests/semantic_ai_eval.py`
- `tests/fixtures/ai_semantic_eval/e1_cases.json`
- `tests/test_metric_truth.py`
- `tests/test_recommendation_tracking.py`
- `tests/test_recommendation_read_write_split.py`
- `tests/test_metrics_c2_fixtures.py`

Note: `app/routes/` and top-level `templates/` do not exist in this repo. The
task-relevant route/template surfaces are `app/web/routes.py` and
`app/templates/coach.html`.

## Checks Run

- `git status --short`: pass, no output before work.
- `git branch --show-current`: pass, `cona`.
- `git rev-parse HEAD`: pass,
  `cef52518ed55d94de6e6fee4dc8c28654baf4328`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py tests/test_ai_coach.py tests/test_coach_first_ui.py tests/test_semantic_ai_eval.py tests/test_recommendation_read_write_split.py tests/test_recommendation_tracking.py tests/test_metrics_c2_fixtures.py -q -p no:cacheprovider`: pass, `69 passed, 1 warning`.

Warning observed:

- Starlette/TestClient deprecation warning from `.venv/lib/python3.14/site-packages/fastapi/testclient.py`.

Final checks:

- `git diff --check`: pass, no output.
- `git status --short`: expected untracked report file only,
  `?? docs/audit/WP-018-01_AI_COACH_QUALITY_BASELINE_AND_GAP_MAP.md`.

## Current AI Coach Pipeline

Input/payload build:

- `app/services/ai_coach.py` builds the AI coach payload in
  `build_ai_coach_payload()`. It reads playable matches, builds summary,
  dashboard status, aim profile, period comparison, map stats, detected
  weaknesses, structured mistakes, coach focus, active/all recommendation
  progress, exact recent matches, Metric Truth definitions and metric
  confidence metadata.
- Payload rules include `do_not_invent_facts`, `use_only_payload_data`,
  `mention_data_gaps`, `use_exact_date_windows_for_trends` and
  `do_not_treat_low_confidence_as_hard_evidence`.
- Default provider is `codex_cli_handoff`. `CodexCliHandoffProvider.prepare()`
  writes `coach_payload.json`, `codex_prompt.md`, `ai_coach_result.md` and
  `metadata.json` into the configured AI handoff directory.
- `local_llm` exists as a scaffold for direct generation via Ollama or an
  OpenAI-compatible local endpoint, but default behavior is handoff.

Prompt behavior:

- `build_ai_coach_prompt()` asks for strict JSON with `summary`,
  `diagnoses[]`, `recommendations[]`, `warnings[]`, `evidence[]` and
  `confidence`.
- The prompt tells AI not to invent facts, to state low confidence, to use
  Metric Truth, to add caveats for approximate/warn metrics and not to use
  suppressed/unavailable metrics as evidence.
- The prompt still asks the AI to discuss `aim`, `map`, `crosshair placement`,
  `grenades`, `entry duels` and `survival`; crosshair placement is correctly
  supposed to be a data gap, but the current wording makes unsupported-domain
  overclaiming a practical risk.

Output validation and fallback:

- `app/services/ai_validator.py` validates structured output before
  persistence/display.
- Required top-level sections are enforced.
- Unknown metric ids are rejected.
- Suppressed/unavailable metrics are rejected for diagnosis,
  recommendation and AI evidence usage.
- Warn metrics require caveats.
- Invalid/free-form output is replaced by safe fallback Markdown that says the
  AI output was rejected and that dashboard, Metric Truth and current
  recommendations remain source of truth.
- `save_ai_coach_result()` stores validator metadata in
  `coach_reports.report_json` as `ai_validation`; valid structured output is
  also stored as `ai_structured_output`.

Display behavior:

- `/coach` in `app/web/routes.py` builds the coach page from existing rows and
  read helpers. It does not generate AI output on page render.
- `app/templates/coach.html` shows the current tracked recommendation, evidence
  and confidence, latest match summary, AI validation state, weak metric notes,
  AI handoff metadata, latest AI report and recommendation history.
- The coach-first view labels the current goal as "Current tracked
  recommendation" and explicitly says it is not a verified top problem.
- AI validation status shows valid structured reports, unknown validation
  metadata or fallback reports.

Fallback behavior:

- AI provider fallback for default `codex_cli_handoff`: direct generation
  raises a runtime message telling the user to paste a Codex result back into
  the UI.
- Validation fallback replaces invalid output with safe Markdown.
- `/coach` empty states show no tracked recommendation, no AI report and no
  latest match without running background jobs.

Caveat/limitation enforcement:

- Runtime Metric Truth is in `app/services/metric_truth.py`.
- Runtime metric confidence/date-window handling is in
  `app/services/metric_confidence.py`.
- Recommendation health rejects legacy baselines, non-playable baseline rows,
  missing metric confidence and hard rules using weak metrics.
- `/coach` surfaces Metric Truth warnings for `early_deaths`, `trade_kills`,
  `side_split_metrics` and `traded_deaths`.
- CS2 domain boundaries are strongest in docs, not fully encoded as a runtime
  payload block.

## Current Quality Baseline

Safe claims:

- AI may summarize structured facts that are present in the payload.
- AI may provide bounded advice when supported by Metric Truth, metric
  confidence, source/date-window confidence, sample coverage and current
  recommendation state.
- AI may state data gaps and review questions.
- AI may discuss current active recommendation progress only as the current
  tracked recommendation, not as a verified top problem or planner-selected
  priority.

Must caveat or suppress:

- Low, unavailable, suppressed, missing, sparse, mixed-source or approximate
  metrics must not become hard diagnosis, recommendation, success/failure or
  progress claims.
- `early_deaths`, `kast`, `hltv_rating`, `swing_score`, `flash_assists` and
  similar warn/approximate metrics require caveats.
- `trade_kills`, side metrics and accuracy are weak/display/warning context
  only.
- `traded_deaths`, `grenade_rating`, `aim_rating`, `crosshair_placement`,
  economy, positioning and clutch are unavailable for hard advice.
- Exact playlist/mode is not accepted in `v0.9`; current output may use only
  `mode_unknown`, `provenance_demo`, `provenance_valve_matchmaking` and exact
  date source where supported.
- Current map labels are source-provided labels, not validated map-pool or
  map-specific coaching proof.

Recommendation `#5` representation:

- Hot docs say recommendation `#5` is the accepted active hard recommendation
  with three real evaluations and progress `3/10`.
- Runtime code does not hard-code numeric recommendation `#5`; it exposes the
  current active survival recommendation through recommendation progress.
- The coach UI represents this as "Current tracked recommendation" and not as
  a planner-selected verified top problem.
- Legacy recommendations are detected and blocked from hard progress if they
  lack confidence metadata or use weak evidence.

Weak metrics:

- Metric Truth registry classifies metrics by reliability and usage decision.
- Validator rejects suppressed/unavailable metrics for hard structured AI
  claims and requires caveats for warn metrics.
- Recommendation health and tests protect against weak metrics driving hard
  progress.

Playlist/mode uncertainty:

- Docs and Hot status require playlist/mode to remain unknown/provenance-only.
- No inspected coach payload field currently provides an explicit
  `mode_unknown`/playlist caveat block to the AI; this is a gap because the AI
  mostly learns the rule indirectly from source docs and limited payload rules.

## Existing Tests / Missing Tests

Existing relevant coverage:

- `tests/test_ai_validator.py`: structured output passes, missing sections
  fail, unknown metrics fail, suppressed/unavailable metrics fail, warn metrics
  need caveats, invalid free-form output saves safe fallback, valid JSON stores
  structured metadata.
- `tests/test_ai_coach.py`: payload uses structured match data, unavailable
  metric confidence appears in payload, exact-date recent matches exclude
  approximate-date matches, Codex handoff writes prompt/payload, AI report
  persistence/history and provider health work.
- `tests/test_coach_first_ui.py`: `/coach` renders empty/current states,
  labels current goal as not verified top problem, surfaces legacy refresh and
  weak metric warnings, shows AI validation fallback/valid states, does not
  mutate recommendation/evaluation rows, and does not run live AI/Steam/parser/
  import jobs on GET.
- `tests/test_metric_truth.py`: core registry, hard-claim eligibility,
  warning semantics, suppressed low/unavailable metrics, unknown metric safety
  and payload serialization.
- `tests/test_recommendation_tracking.py`: default survival recommendation,
  baseline confidence, legacy detection, evaluation confidence evidence,
  legacy skip behavior and progress gating.
- `tests/test_recommendation_read_write_split.py`: read helpers and GET
  surfaces do not create recommendation/evaluation rows.
- `tests/test_semantic_ai_eval.py` and
  `tests/fixtures/ai_semantic_eval/e1_cases.json`: local deterministic
  semantic checks for unsupported hard wording, confidence overstatement,
  hallucinated metrics, missing caveats, no-data hard advice, missing
  `metric_confidence` and missing evidence links.
- `tests/test_metrics_c2_fixtures.py`: metric confidence/date-window fixture,
  docs/Metric Truth sync, golden aggregate outputs and null/empty metrics.

Missing coverage / snapshot gaps:

- No prompt snapshot test for current `build_ai_coach_prompt()` language.
- No payload contract snapshot proving explicit prompt/payload versions,
  metric-registry snapshot/version and CS2 domain constraints.
- Semantic AI eval is fixture-only; it is not integrated into
  `save_ai_coach_result()` runtime validation.
- Runtime validator does not require `metric_confidence` inside `evidence[]`
  and does not require the full `problem -> metric -> match -> recommendation`
  evidence chain.
- No targeted test proving the prompt blocks exact playlist/mode claims,
  economy, positioning, clutch, map-certainty or crosshair-placement advice
  unless stated as unavailable/data gap.
- No targeted test proving recommendation `#5` / current tracked
  recommendation is carried into AI payload with enough evidence for calibrated
  wording without claiming verified planner priority.

Safe commands for future targeted work:

- `APP_ENV=test .venv/bin/pytest tests/test_ai_validator.py -q`
- `APP_ENV=test .venv/bin/pytest tests/test_metric_truth.py tests/test_ai_validator.py -q`
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_semantic_ai_eval.py -q -p no:cacheprovider`
- `APP_ENV=test .venv/bin/pytest tests/test_coach_first_ui.py -q`
- `APP_ENV=test .venv/bin/pytest tests/test_recommendation_read_write_split.py tests/test_ai_validator.py tests/test_coach_first_ui.py -q`

## Gap Map

### P0

Gap: Runtime AI output lacks accepted versioned evidence identity.

- Evidence: `docs/AI_COACH.md` requires `prompt_version`,
  `payload_version` and `metric_registry_version` before future AI advice can
  be treated as accepted versioned evidence. `app/services/ai_coach.py`
  persists a payload hash and full payload snapshot, but no explicit prompt,
  payload or metric-registry version fields.
- Risk: AI reports cannot be audited reliably after prompt/metric policy
  changes; calibrated WP-018 evidence may become non-reproducible.
- Blocks WP-018 implementation: yes.
- Recommended fix type: code/test/design.
- Suggested next task ID:
  `WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`.

Gap: Prompt/payload domain constraints are incomplete at runtime.

- Evidence: `docs/CS2_DOMAIN_CONTRACT.md` blocks exact playlist/mode,
  economy, positioning, clutch, hard trade and crosshair-placement claims.
  `build_ai_coach_prompt()` asks the model to discuss crosshair placement and
  similar areas, with only a narrow instruction to mark crosshair as a data
  gap. The payload has Metric Truth data but no explicit domain constraints
  object carrying playlist/mode and unavailable-model rules.
- Risk: Provider output may pass schema/metric validation while still making a
  semantically unsupported CS2 claim through wording, rationale or a weak proxy
  metric.
- Blocks WP-018 implementation: yes.
- Recommended fix type: prompt/payload/test.
- Suggested next task ID:
  `WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`.

### P1

Gap: Runtime validator is weaker than the semantic eval contract.

- Evidence: `tests/semantic_ai_eval.py` checks confidence overstatement,
  supplied-evidence membership, no-data behavior, metric confidence and the
  `problem -> metric -> match -> recommendation` chain. `validate_ai_coach_output()`
  checks schema and Metric Truth usage but does not require those semantic
  fields at runtime.
- Risk: Valid structured output can still be under-evidenced for accepted
  advice.
- Blocks WP-018 implementation: yes.
- Recommended fix type: code/test/design.
- Suggested next task ID: `WP-018-03_AI_COACH_RUNTIME_SEMANTIC_GUARDS`.

Gap: No prompt/payload golden snapshot tests.

- Evidence: Existing tests check selected payload fields and handoff file
  creation, but not stable prompt text, domain-constraint payload content or
  version/snapshot fields.
- Risk: Future prompt or payload edits can silently weaken caveats or remove
  guardrails.
- Blocks WP-018 implementation: yes.
- Recommended fix type: test.
- Suggested next task ID:
  `WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`.

Gap: AI payload does not explicitly encode playlist/mode uncertainty.

- Evidence: Hot docs and domain docs require provenance-only playlist/mode in
  `v0.9`. The inspected payload rules include exact date windows and Metric
  Truth but no explicit `mode_unknown` or playlist/mode caveat object.
- Risk: AI can imply Premier/Competitive/FACEIT/custom context from nearby
  source labels or CS2 assumptions.
- Blocks WP-018 implementation: yes.
- Recommended fix type: payload/test/prompt.
- Suggested next task ID:
  `WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`.

### P2

Gap: Current coach focus and coach rules predate the stricter planner contract.

- Evidence: `build_coach_focus()` selects the first detected weakness and
  attaches canned actions. The UI separately labels current recommendation as
  not a verified top problem, but the older "Главный фокус" section still
  displays rule-based focus content.
- Risk: Users may confuse rule-based focus with planner-verified primary
  problem selection.
- Blocks WP-018 implementation: no, if kept visibly caveated.
- Recommended fix type: UI copy/test/design.
- Suggested next task ID: `WP-018-04_COACH_FOCUS_LABEL_CALIBRATION`.

Gap: Recommendation `#5` identity is documented but not a stable payload
  contract.

- Evidence: Hot docs identify recommendation `#5`; runtime payload serializes
  active/all recommendation progress but does not have a specific accepted
  `current_accepted_recommendation` contract field.
- Risk: AI output may describe "current recommendation" without enough
  explicit status/evidence to distinguish accepted active focus from other
  category goals.
- Blocks WP-018 implementation: no, but it limits calibration quality.
- Recommended fix type: payload/test/design.
- Suggested next task ID: `WP-018-05_ACCEPTED_RECOMMENDATION_PAYLOAD_CONTRACT`.

Gap: Provider-specific structured response enforcement is shallow.

- Evidence: `local_llm` asks for JSON in prompt and validator rejects invalid
  output after generation; there is no provider-native JSON/schema mode.
- Risk: More invalid outputs and more fallback reports when direct provider
  generation is used.
- Blocks WP-018 implementation: no for default handoff; yes for future direct
  provider quality.
- Recommended fix type: code/test/provider design.
- Suggested next task ID: `WP-018-06_PROVIDER_STRUCTURED_OUTPUT_HARDENING`.

### P3

Gap: AI validation metadata is stored inside `coach_reports.report_json`.

- Evidence: Stage 8 intentionally stores validation metadata in the existing
  report JSON, not a dedicated structured table.
- Risk: Querying/reporting validation status is less ergonomic.
- Blocks WP-018 implementation: no.
- Recommended fix type: design/docs, maybe future schema task only with
  explicit DB authorization.
- Suggested next task ID: `WP-020_AI_REPORT_STORAGE_REVIEW` if later needed.

Gap: `/coach` artifact overview remains acceptable only at current scale.

- Evidence: Hot docs and Known Limitations say `/coach` artifact overview is
  acceptable at 22 demos but should be optimized before materially larger demo
  volume.
- Risk: Performance/UX degradation at larger demo counts.
- Blocks WP-018 implementation: no.
- Recommended fix type: UI/performance design.
- Suggested next task ID: outside WP-018 unless quality scope explicitly needs
  display performance.

## Recommended First Implementation Task

`WP-018-02_AI_COACH_PROMPT_PAYLOAD_VERSION_SNAPSHOT`

Purpose: add a narrow no-schema prompt/payload contract update and golden tests
so AI handoff payloads include explicit `prompt_version`, `payload_version`,
`metric_registry_version` or registry snapshot identifier, and a visible
`domain_constraints` block covering playlist/mode uncertainty, unavailable
economy/positioning/clutch/crosshair models, weak metric rules and
recommendation evidence boundaries.

Why first:

- It directly addresses both P0 gaps.
- It is narrow and testable.
- It can avoid DB/schema changes by using existing payload/report JSON fields.
- It creates the stable evidence base needed before runtime semantic guard
  hardening.

Suggested checks for that task:

- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_ai_coach.py tests/test_ai_validator.py tests/test_semantic_ai_eval.py -q -p no:cacheprovider`
- Add or update a focused prompt/payload snapshot test in the same task.
- `git diff --check`
- `git status --short`

## Safety Notes

- No DB, schema, data, upload, raw demo, import, parser, evaluator, manual
  evaluator, runtime, deploy or package files were changed.
- No live Steam/Valve import was run.
- No parser/evaluator/manual evaluator jobs were run.
- No services were restarted.
- No package install or dependency change was made.
- No public/friends readiness or `v1.0` claim is made.
- Playlist/mode remains unknown/provenance-only.
- Weak metrics remain caveated or suppressed according to Metric Truth.
- Major CS2 feature work and unrestricted WP-018 expansion remain paused.
