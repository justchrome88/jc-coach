# WP-018A Coach Output Quality Diagnosis Report

## 1. Summary

Result: PASS_WITH_WARNINGS.

This diagnostic inspected the repo-visible coach/recommendation output path after v0.9 Real Data Onboarding. No repair edits were made. The current system has important safety controls: legacy recommendations are marked `needs_refresh`, invalid AI output is replaced by a validator fallback, Metric Truth warnings are visible on `/coach`, and playlist-specific mode claims were not found in the inspected active output path.

The main remaining quality risk is that deterministic rule-based coach output can still sound more certain than the evidence allows. The strongest issue is survival scoring: `early_deaths` is documented as warning-only, but it still participates in green/yellow/red survival evaluation.

Finding counts:

| Severity | Count |
| --- | ---: |
| P0 | 0 |
| P1 | 3 |
| P2 | 5 |
| P3 | 3 |

## 2. Preflight

- pwd: `/opt/jc-coach`
- branch: `main`
- git status before: clean
- latest commits:
  - `677d74d (HEAD -> main) Add control-plane protection policy`
  - `e6d5cd4 Add agent invocation and output modes`
  - `68a42a4 Promote real data onboarding to v0.9 with warnings`
  - `4b53f4b Add agent role cards and handoff protocol`
  - `5278596 Clean up legacy documentation pointers`
  - `dcb9239 (origin/main) Add legacy documentation currency snapshot`
  - `344739d Add task type profiles and prompt contract`
  - `00726c4 Add repo-native agent workflow and docs steward`

## 3. Inspection Method

Commands/approach used:

- `pwd`
- `git status --short`
- `git branch --show-current`
- `git log --oneline -8 --decorate`
- `rg --files app tests`
- targeted `rg` for coach, recommendation, AI validation, progress, Metric Truth, playlist/public wording
- targeted `sed`/`nl -ba` reads of relevant code, templates, docs and tests

No tests were run. No app endpoints were called. No DB reads or mutations were performed.

## 4. Inspected Inventory

Inspected docs:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/project_management/AGENT_WORKFLOW.md`
- `docs/AI_COACH.md`
- `docs/RECOMMENDATIONS.md`
- `docs/METRICS.md`
- `docs/KNOWN_LIMITATIONS.md`

Inspected code/services:

- `app/web/routes.py`
- `app/api/routes.py`
- `app/services/recommendation_tracking.py`
- `app/services/ai_coach.py`
- `app/services/ai_validator.py`
- `app/services/metric_truth.py`
- `app/services/metric_confidence.py` by references/search
- `app/services/analytics.py` by references/search
- `app/services/aim_stats.py`
- `app/services/coach_rules.py`
- `app/services/mistake_detection.py`
- `app/services/report_generator.py`

Inspected templates/static output surfaces:

- `app/templates/coach.html`
- `app/templates/dashboard.html`
- `app/templates/stats.html`
- `app/templates/report.html`
- `app/templates/match_detail.html` by file inventory/search only
- `app/static/charts.js` by file inventory/search only

Inspected tests:

- `tests/test_recommendation_tracking.py`
- `tests/test_ai_validator.py`
- `tests/test_coach_first_ui.py`
- `tests/test_report_generator.py` by targeted search/sample
- `tests/test_metric_truth.py` by targeted search only
- `tests/test_aim_stats.py` by targeted search only
- `tests/test_web_smoke.py` by targeted search only

Areas not inspected deeply:

- Parser internals, importer internals and Steam integration internals. They are data production paths, not coach wording/output paths for this diagnostic.
- Old audit reports beyond targeted samples/search. They were treated as evidence/history only.
- Live generated reports and handoff files under runtime data. The task forbids generating persistent app reports and did not require reading runtime state.

## 5. Findings By Severity

### P0 Findings

None found.

No inspected active output path made a materially false product claim at P0 level. No inspected active path claimed friends/public readiness, exact playlist mode, or unvalidated AI authority as current truth.

### P1-1: Warning-only `early_deaths` still participates in hard survival scoring

- File/path: `app/services/recommendation_tracking.py`
- Function: `_signals`, `_compare_lower`, `_status_score_comment`
- Evidence: survival branch compares `early_deaths` against `early_deaths_per_match` and appends positive/negative signals at `app/services/recommendation_tracking.py:773`. `_compare_lower` blocks metrics only when `usage_decision(...) != "allowed"` at `app/services/recommendation_tracking.py:844`, and Metric Truth defines `early_deaths` recommendation usage as `warn`, so the call appends a missing signal. However, legacy tests still encode survival green/yellow/red expectations with `early_deaths` as part of the scenario, and output wording still references first/early deaths together.
- Why it matters: v0.9 limitations say `early_deaths` is approximate/warning-only and must not become hard recommendation evidence. If scoring or comments are understood as hard evaluation, the coach can overclaim a survival result.
- Recommended follow-up WP/slice: WP-018B.
- Repair timing: WP-018B.

### P1-2: Multi-category active goal surface can imply accepted progress for legacy/non-primary recommendations

- File/path: `app/templates/coach.html`
- Function/template area: "Активные цели по направлениям"
- Evidence: the card loop renders every `all_recommendation_progress` item with `progress_score`, Green/Yellow/Red counts and category status at `app/templates/coach.html:375`. It does not render each item health/needs-refresh/accepted-for-hard-progress caveats, unlike the primary current recommendation block at `app/templates/coach.html:40` and `app/templates/coach.html:53`.
- Why it matters: Hot context says only recommendation `#5` survival is currently accepted for hard progress, while legacy `#1`, `#3` and `#4` must not receive new hard evaluations unless refreshed. This lower page section can make non-primary or stale category progress appear equally valid.
- Recommended follow-up WP/slice: WP-018B or WP-018C.
- Repair timing: WP-018B if the page is the primary coach surface; otherwise WP-018C.

### P1-3: Public API exposes progress fields without the same caveat density as coach UI

- File/path: `app/api/routes.py`
- Routes: `/recommendations/active`, `/recommendations`, `/recommendations/categories`
- Evidence: API serializers return health plus `progress_score`, counts, completed/target and summary at `app/api/routes.py:160` and `app/api/routes.py:181`. Category summaries return accepted flags at `app/api/routes.py:221`, but the routes do not provide UI-like warning text, Metric Truth caveats, or "not verified top problem" wording.
- Why it matters: API consumers can display hard progress claims without the guardrails already present on `/coach`. This is not a friends/public readiness issue by itself, but it is a likely misleading output path if reused by a client.
- Recommended follow-up WP/slice: WP-018C.
- Repair timing: WP-018C or deferred until an API/UI consumer exists.

### P2-1: Latest-match coach summary displays approximate/warn metrics without local caveats

- File/path: `app/templates/coach.html`
- Template area: "Последний матч"
- Evidence: latest match displays ADR/KAST and entry deaths at `app/templates/coach.html:127` through `app/templates/coach.html:134`. KAST is approximate/warn in Metric Truth, and entry deaths are medium reliability. The page has a separate Metric Truth warnings section, but the local latest-match card has no inline confidence/caveat.
- Why it matters: users scan cards locally. The local card can look like fully trusted match truth.
- Recommended follow-up WP/slice: WP-018C.
- Repair timing: WP-018C.

### P2-2: Deterministic structured mistake detector emits confident coach claims without Metric Truth metadata

- File/path: `app/services/mistake_detection.py`
- Functions: `_global_mistakes`, `_match_mistakes`, `category_scorecard`, `match_coach_sections`
- Evidence: the detector emits high/medium severity and confidence labels for KAST, entry deaths, utility and map facts at `app/services/mistake_detection.py:114`. Match coach sections use KAST, early deaths and utility facts at `app/services/mistake_detection.py:66`. The objects do not carry metric ids, usage decisions, reliability, caveats or date-window metadata.
- Why it matters: these objects feed coach categories, structured mistakes and AI payload. The wording can become action-driving advice without the Metric Truth caveat density used elsewhere.
- Recommended follow-up WP/slice: WP-018D.
- Repair timing: WP-018D.

### P2-3: Aim interpretation can overstate "aim impact" from ADR/HS/opening-duel proxy data

- File/path: `app/services/aim_stats.py`, `app/templates/coach.html`, `app/templates/stats.html`
- Functions/template areas: `_interpretation`, `get_aim_profile`, aim profile sections
- Evidence: `_interpretation` says "Aim impact выглядит сильным" or "Aim impact рабочий" based on ADR/HS thresholds at `app/services/aim_stats.py:75`. The same profile explicitly lists gaps for accuracy, first bullet accuracy, spray control, TTK and crosshair placement at `app/services/aim_stats.py:17`, and templates render the interpretation prominently at `app/templates/coach.html:261`.
- Why it matters: after v0.9, coach quality should distinguish evidence-backed claims from weak claims. ADR/HS/opening-duel success can indicate damage/duel outcomes, but not full aim quality or crosshair placement.
- Recommended follow-up WP/slice: WP-018D.
- Repair timing: WP-018D.

### P2-4: Report generator writes training-plan language from heuristic focus without per-action evidence links

- File/path: `app/services/report_generator.py`
- Function: `render_markdown_report`
- Evidence: the report includes a main focus, top problems and a seven-day training plan at `app/services/report_generator.py:106` through `app/services/report_generator.py:190`. It includes one global caveat at `app/services/report_generator.py:117`, but individual focus/actions are not tied to metric ids, confidence, or accepted recommendation state.
- Why it matters: persistent reports can outlive the UI context and are likely to be read as canonical coaching advice. A one-time caveat may not sufficiently constrain later action text.
- Recommended follow-up WP/slice: WP-018E.
- Repair timing: WP-018E.

### P2-5: AI validator checks structure and metric ids, but not semantic entailment of claims

- File/path: `app/services/ai_validator.py`
- Function: `validate_ai_coach_output`
- Evidence: validator enforces required sections, confidence enum, metric id validity, suppression and caveat presence at `app/services/ai_validator.py:39` through `app/services/ai_validator.py:125`. It does not verify that claim text is entailed by payload values or that a high-confidence claim matches current sample/date-window limits.
- Why it matters: an AI output can pass schema and metric-id checks while still overstating a trend or making a vague action claim. This is already acknowledged as a future gap in `docs/KNOWN_LIMITATIONS.md`, so this is a known P2 risk, not a blocker.
- Recommended follow-up WP/slice: WP-018F.
- Repair timing: WP-018F or deferred if deterministic wording is fixed first.

### P3-1: Recommendation descriptions still mention weak metrics in primary prose

- File/path: `app/services/recommendation_tracking.py`
- Data: `RECOMMENDATION_DEFINITIONS`
- Evidence: survival description says to reduce `entry deaths and early deaths` at `app/services/recommendation_tracking.py:30`. Metric Truth warnings later clarify early deaths, but primary copy still places it next to entry deaths.
- Why it matters: this can nudge users to treat early deaths as equally reliable.
- Recommended follow-up WP/slice: WP-018B.
- Repair timing: WP-018B or WP-018C.

### P3-2: Coach category scorecard shows "100" when no mistakes exist

- File/path: `app/services/mistake_detection.py`, `app/templates/coach.html`
- Function/template area: `category_scorecard`, "Категории тренера"
- Evidence: categories without mistakes get `score = 100` unless crosshair/economy no-data at `app/services/mistake_detection.py:47`; template displays the score at `app/templates/coach.html:250`.
- Why it matters: absence of detected mistakes is not proof of perfect category quality, especially with limited data coverage.
- Recommended follow-up WP/slice: WP-018D.
- Repair timing: WP-018D.

### P3-3: Generated report route remains one click from `/coach`

- File/path: `app/templates/coach.html`, `app/web/routes.py`, `app/services/report_generator.py`
- Route/template area: `/report/generate`
- Evidence: `/coach` includes "Сгенерировать отчёт" at `app/templates/coach.html:13`; route calls `generate_report(db)` at `app/web/routes.py:1008`; service writes a DB `CoachReport` and filesystem report file at `app/services/report_generator.py:25` and `app/services/report_generator.py:78`.
- Why it matters: this is an explicit POST, so not a hidden side effect. But report generation creates persistent coach advice and should inherit WP-018 quality constraints before broader use.
- Recommended follow-up WP/slice: WP-018E.
- Repair timing: WP-018E or deferred.

## 6. Required Explicit Checks

### Playlist-Specific Claims Despite v0.9 Match-Mode Deferral

No active inspected coach/recommendation output path claimed exact Premier/Competitive/Wingman playlist labels. The inspected code uses map names, source labels and match results. v0.9 limitation remains respected.

### Hard Progress Claims For Legacy Recommendations #1, #3, #4

Primary current recommendation UI includes a `needs_refresh` warning and hides hard progress acceptance when health is not accepted. `recommendation_health` marks legacy recommendations as not accepted for hard progress when confidence, playable baseline, rule, or evaluation evidence is stale.

Risk remains in lower multi-category cards and API serialization, which can present progress scores/counts without the same local warning text.

### Progress Claims For Active Recommendation #5 Beyond Accepted Evidence

The active survival recommendation path is scoped to target matches, counts and `progress_score`. It shows "Current tracked recommendation" and "not verified top problem" in the primary card. However, survival scoring should be tightened to ensure warning-only `early_deaths` cannot influence accepted hard progress.

### Hard Claims From Approximate, Low, Unavailable Or Suppressed Metrics

AI validator blocks suppressed/unavailable metrics and requires caveats for warn metrics. The deterministic mistake/aim/report surfaces are weaker: they have fewer metric ids and caveats attached to each claim.

### Missing Caveats For Approximate/Warn Metrics

Missing or weak caveat placement was found in latest-match card, aim interpretation, structured mistakes and persistent report actions.

### AI Output Bypassing Stage 8 Validator Semantics

The save path validates AI output and falls back for invalid content at `app/services/ai_coach.py:144`. Tests cover free-form output fallback. No direct bypass was found in the inspected save/display path. Remaining risk is semantic entailment, not bypass.

### UI/API Wording That Implies Friends/Public Readiness

No inspected coach/recommendation output path implied friends/public readiness. Config/tests still reference public-readiness secrets, but the current user-facing coach wording does not advertise friends/public use.

### Weak Parser Facts, Side Splits, Trade Metrics, Early Deaths Or Map/Mode Claims As Fully Trusted

Trade metrics, side splits and unavailable metrics are mostly suppressed or caveated. Early deaths remain the main risk because survival evaluation and prose still involve it. Map-specific output uses map names and winrate/ADR, not playlist/mode labels, but map weakness/action wording should gain sample and caveat attachment.

### Actionability Problems

Several actions are concrete enough for next match, especially survival "first 20 seconds" advice. Some heuristic outputs remain broad, such as category scorecards, aim interpretation and seven-day report plan. They should be tightened to evidence-linked next-match behavior.

## 7. Recommended Follow-Up Slices

### WP-018B: Recommendation Scoring Semantics

Goal: make active recommendation scoring fully Metric Truth aligned.

Scope:

- Remove warning-only metrics from hard status scoring.
- Ensure survival progress for #5 is based on accepted metrics only.
- Update comments/descriptions so early deaths is labeled as context/warning.
- Add tests proving `early_deaths` cannot turn a match green/red by itself.

### WP-018C: Coach UI/API Caveat Density

Goal: make displayed progress and latest-match facts harder to overread.

Scope:

- Add local caveats to latest-match metric displays.
- Add health/accepted labels to all category progress cards.
- Add warning fields or explicit caveat text to recommendation API serializers.
- Keep "current tracked recommendation, not verified top problem" visible.

### WP-018D: Structured Mistakes And Aim Claims Calibration

Goal: attach Metric Truth metadata and soften unsupported claims in deterministic mistake/aim outputs.

Scope:

- Add metric ids/reliability/caveats to structured mistakes.
- Avoid "100" category score when absence of detection means unknown/ok.
- Reword aim profile to damage/duel proxy, not full aim/crosshair truth.

### WP-018E: Persistent Report Wording Calibration

Goal: make generated reports durable and caveated enough to stand alone.

Scope:

- Tie report focus/actions to metric ids and confidence.
- Mark report generation as explicit persistent advice.
- Avoid hard claims from weak trends or low sample map stats.

### WP-018F: AI Validator Semantic Guardrails

Goal: reduce valid-JSON overclaim risk.

Scope:

- Add claim/action linting for forbidden phrases and high-confidence overclaims.
- Require evidence ids and caveats for each recommendation action.
- Optionally cross-check confidence against payload metric confidence.

## 8. Positive Controls Already Present

- `AGENTS.md` blocks DB/import/parser/evaluator/service changes without authorization.
- `/coach` GET is covered by tests for no mutation and no live AI/Steam/parser/import jobs.
- AI free-form output is rejected and stored as safe fallback.
- Metric Truth warnings appear on `/coach`.
- Legacy recommendation health can mark stale baselines/evaluations/rules as not accepted.
- Primary coach card says "Current tracked recommendation" and explicitly not "verified top problem".
- v0.9 playlist mode limitation is not contradicted in inspected active output code.

## 9. Risks / Remaining Gaps

- This was static repo inspection only; no runtime DB state was inspected.
- The report did not run tests, start the app, generate reports, or validate rendered HTML from current production data.
- Some findings are about wording and semantics, so final severity should be rechecked after seeing actual v0.9 live data output.
- Deterministic code paths need the same rigor as AI validation because users see deterministic advice as product truth.

## 10. What Was Intentionally Not Changed

- no code changed
- no templates changed
- no tests changed
- no canonical status/control-plane docs changed
- no DB changed
- no live Steam/Valve import ran
- no parser jobs ran
- no evaluator/manual evaluator jobs ran
- no service/nginx/deploy config changed
- no persistent app reports generated
- no product logic changed
- no git add/commit/push performed

## 11. Verdict

PASS_WITH_WARNINGS.

JC Coach can proceed with WP-018 implementation slices. The first safe implementation slice should be WP-018B: Recommendation Scoring Semantics, because it addresses the highest-risk mismatch between Metric Truth and accepted progress.

## 12. Checks

Planned after report creation:

- `git diff --check`
- `git diff --stat`
- `git status --short`
