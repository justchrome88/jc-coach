# MVP-005 AI Coach Data Contract Vertical Slice

Date: 2026-07-09

Task: `MVP-005_AI_COACH_DATA_CONTRACT_VERTICAL_SLICE`

Mode: Executor diagnostic/contract work, report-only

Verdict: `PASS_WITH_WARNINGS`

## Summary

MVP-005 defines the first end-to-end AI coach contract from parser evidence to
coach output. No product code, DB schema, data, parser job, evaluator job,
import job, service config, package config or raw demo lifecycle work was
changed or executed.

The current codebase already has enough quality infrastructure to constrain the
first slice: parser artifact confidence metadata, normalized parser tables,
Metric Truth, metric confidence, AI coach payload/domain snapshots, semantic
validation, safe fallback rendering and accepted/rejected output-quality
fixtures. The missing piece is a canonical first-slice contract that future WPs
can implement incrementally without allowing unsupported coach claims.

The recommended path after this task is to start the canonical Phase 6 sequence
at `WP-060`, not to create a competing MVP numbering system.

## Sources Read

- `AGENTS.md`
- `/opt/jc-coach-pm/AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `/opt/jc-coach-pm/task_cards/mvp_queue_compact_v1/2026-07-09_MVP-005_AI_COACH_DATA_CONTRACT_VERTICAL_SLICE_task-card.md`
- `/opt/jc-coach-pm/indexes/current_context_manifest.json`
- `/opt/jc-coach-pm/docs/task_card_profiles/MVP_TASK_CARD_SAFETY_PROFILES.md`
- `docs/METRICS.md`
- `app/db/models.py`
- `app/services/ai_coach.py`
- `app/services/ai_validator.py`
- `app/services/analytics.py`
- `app/services/coach_rules.py`
- `app/services/demo_parser.py`
- `app/services/metric_confidence.py`
- `app/services/metric_truth.py`
- `app/services/mistake_detection.py`
- `app/services/recommendation_tracking.py`
- `tests/semantic_ai_eval.py`
- `tests/test_ai_coach.py`
- `tests/test_ai_output_quality_fixtures.py`
- `tests/test_ai_validator.py`
- `tests/test_demo_parser.py`
- `tests/test_metrics_c2_fixtures.py`
- `tests/test_parser_facts_confidence.py`
- `tests/test_semantic_ai_eval.py`
- `tests/fixtures/metrics/golden_aggregate_c2.json`
- `tests/fixtures/parser/sanitized_parser_payload_c2.json`

## Existing Quality Infrastructure

Current accepted infrastructure relevant to this vertical slice:

| Area | Existing support | Contract implication |
|---|---|---|
| Parser artifacts | `DemoParseArtifact` stores parser name/version, payload version, status, source demo path, demo SHA1, event counts, confidence, gaps and payload JSON. | The first slice must preserve parser provenance and event coverage as first-class evidence. |
| Normalized parser tables | Current models include `DemoRound`, `DemoPlayerRound`, `DemoWeaponStat`, `DemoDamageEvent`, `DemoDuel` and `DemoGrenadeEvent`. | Future derived context should consume normalized tables, not raw parser JSON alone. |
| Metric Truth | `metric_truth.py` defines stable metric ids, reliability and usage policy. `docs/METRICS.md` is synchronized by tests. | Every metric used by Scout, Validator or coach output must be registered and usage-gated. |
| Metric confidence | `metric_confidence.py` combines source/sample/date/parser coverage into metric confidence labels. | Hard claims require metric confidence and cannot exceed the weakest evidence link. |
| AI payload snapshot | `ai_coach.py` emits prompt, payload, metric registry and snapshot contract versions. | Scout and Validator payloads must carry version metadata from the start. |
| Domain contract | `ai_coach.py` emits CS2 guardrails for playlist uncertainty, public/friends blocked status, Steam import cap, recommendation policy and unavailable models. | The slice must carry domain guardrails through every stage, not only final output. |
| Semantic validation | `ai_validator.py` rejects missing required sections, unknown/suppressed metrics, unsupported playlist/public/v1 claims, unsupported model claims, missing evidence links and weak-metric hard advice. | Evidence Validator should extend this deterministic pattern rather than rely on LLM judgment. |
| Safe fallback | Invalid AI output is saved as rejected fallback markdown with validation issues, without storing accepted structured output. | Coach output must fail closed and keep debuggable rejection reasons. |
| Fixtures | Output-quality and semantic fixtures cover accepted/rejected cases, safe fallback, confidence, weak metrics, recommendation #5, public/friends and unsupported model claims. | New slice fixtures should mirror this accepted/rejected structure for Scout candidates, insight cards and missions. |

Warnings to preserve:

- Public/friends readiness remains blocked.
- `v1.0` is not claimed.
- Playlist/mode remains unknown or provenance-only.
- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1`.
- Recommendation `#5` remains the accepted active hard recommendation.
- Legacy recommendations `#1`, `#3` and `#4` must not receive new hard evaluations without explicit refresh.
- Weak metrics remain caveated; missing metric confidence blocks hard advice.
- Economy, positioning, clutch, hard trade, crosshair placement, exact playlist and canonical map certainty remain unavailable unless future accepted WPs add reliable evidence.

## First Vertical Slice Data Contract

The first slice should use one versioned envelope at every stage:

```text
parser artifact
  -> normalized events
  -> derived context
  -> metric snapshots
  -> AI Scout candidate insight
  -> Evidence Validator decision
  -> insight card
  -> mission and checkpoints
  -> coach output
```

Required envelope fields for every stage:

| Field | Required value |
|---|---|
| `contract_version` | Stage-specific version string, for example `parser-artifact-v1`, `normalized-events-v1`, `derived-context-v1`. |
| `source_stage` | Previous stage id. |
| `generated_by` | Service/module name. |
| `generated_at` | UTC timestamp. |
| `match_ids` | Accepted match ids used. |
| `source_refs` | Artifact ids, table ids or payload hashes used. |
| `metric_ids` | Registered Metric Truth ids used or emitted. |
| `metric_confidence` | Per metric confidence payload, never omitted for evidence-bearing metrics. |
| `sample` | Match count, round count, opportunity count and omitted/missing counts where known. |
| `domain_guardrails` | Domain policy snapshot, including playlist, recommendation, public readiness and unavailable-model boundaries. |
| `data_gaps` | Explicit missing evidence, not implied values. |
| `validator_status` | `unvalidated`, `accepted`, `accepted_with_warnings` or `rejected`. |

### Stage Contracts

| Stage | Input | Output | Must not do |
|---|---|---|---|
| Parser artifact | Raw demo and parser output when explicitly authorized by a future WP. | Parser artifact with event counts, parser confidence, data gaps and raw/deep payload reference. | Do not infer exact playlist, economy, positioning, clutch, crosshair or traded-death facts. |
| Normalized events | `DemoParseArtifact` plus normalized parser tables. | Event envelopes for rounds, player rounds, damage, duels, weapon stats and grenade events. | Do not treat low-confidence side/trade fields as hard facts. |
| Derived context | Normalized events plus match metadata. | Fight episodes, round context, utility events, opportunity windows and player involvement facts. | Do not fill gaps with heuristics unless marked as heuristic and blocked from hard advice. |
| Metric snapshots | Derived context plus Metric Truth. | Metric values with source, formula, coverage, confidence and usage decision. | Do not output suppressed/unavailable metrics as evidence. |
| AI Scout candidate | Metric snapshots plus domain contracts. | Candidate insight with problem, evidence chain, confidence and proposed mission. | Do not produce user-facing advice or bypass Validator. |
| Evidence Validator | Scout candidate plus source evidence. | Accepted/rejected decision, issue codes and safe fallback reason. | Do not ask an LLM to approve unsupported evidence. |
| Insight card | Validator-accepted candidate. | Durable card payload for UI and coach output. | Do not persist rejected candidates as accepted cards. |
| Mission | Accepted insight card. | Mission with checkpoints, target window and tracking metrics. | Do not make progress/failure claims without future metric snapshots. |
| Coach output | Accepted card plus active mission state. | Caveated user-facing output. | Do not claim certainty beyond validated evidence. |

## Domain Contract: Impact Leak

Purpose: identify when accepted individual impact metrics do not translate into
round or match outcomes, without inventing economy, positioning or clutch
models.

Allowed evidence:

- `result`, `round_score`, `winrate` and round differential when source/date/sample policy passes.
- `kills`, `deaths`, `kd_ratio`, `adr`, `entry_kills`, `entry_deaths` and `utility_damage` when registered usage and metric confidence allow.
- `kast`, `hltv_rating`, `swing_score`, `flash_assists`, `enemies_flashed` and `headshot_rate` only as caveated context when usage is `warn`.
- Match/map windows only when sample and exact-date policy are carried.

Disallowed evidence:

- Economy model, buy strategy, force-buy decisions or save calls.
- Positioning, rotations, spacing, angle discipline, heatmaps or crosshair placement.
- Clutch conversion or clutch mistakes.
- Traded/untraded death rate.
- Exact playlist/mode labels.

Candidate shape:

| Field | Requirement |
|---|---|
| `problem_id` | `impact_leak` |
| `claim` | Bounded wording: "impact is not clearly converting into wins/rounds" or equivalent caveated statement. |
| `evidence_metrics` | At least one outcome metric plus at least one impact metric. |
| `minimum_confidence` | `medium` for hard candidate; otherwise context-only. |
| `window` | Match ids, exact-date status, sample count and omitted count. |
| `caveats` | Required when any `warn`, mixed-source, sparse or approximate metric contributes. |
| `blocked_if` | Missing outcome metric, missing impact metric, suppressed metric, no metric confidence, sample below threshold for pattern claims or unsupported domain wording. |

First-slice acceptance rule:

`impact_leak` may become a Validator-accepted insight only when outcome evidence
and impact evidence both pass Metric Truth usage, sample/window policy and
confidence policy. If the impact metric is `warn`, the card can be accepted
only as `accepted_with_warnings`, not as a hard progress or failure statement.

## Domain Contract: Bad Fight Selection

Purpose: identify repeated low-value or avoidable fight choices using supported
duel and survival facts, without claiming positioning, economy, clutch or exact
trade models.

Allowed evidence:

- `entry_deaths`, `entry_kills`, deaths, ADR, K/D and round result when source and confidence allow.
- Parser duel facts such as opening duel and kill/death event order when parser confidence is carried.
- `early_deaths` only as approximate/warn evidence when timing anchors exist.
- `kast` only as caveated participation context.

Disallowed evidence:

- "You took a bad angle" unless accepted position/view-angle evidence exists.
- "You were untraded" from current data.
- "Bad rotation", "bad spacing", "bad economy fight" or clutch diagnosis.
- Exact team strategy claims from current parser artifacts.

Candidate shape:

| Field | Requirement |
|---|---|
| `problem_id` | `bad_fight_selection` |
| `claim` | Bounded wording: "opening fights are too costly" or "fight timing appears risky from entry-death evidence". |
| `evidence_metrics` | `entry_deaths` plus at least one supporting metric such as `entry_kills`, deaths, ADR or round result. |
| `minimum_confidence` | `medium` for entry-duel facts; `low` or approximate facts force caveat/context-only. |
| `window` | Match ids, round/opportunity count where known and sample warnings. |
| `caveats` | Required for parser event-order limitations and any `early_deaths` use. |
| `blocked_if` | Candidate depends on positioning/trade/clutch/economy claims, missing metric confidence, suppressed metrics or no match/opportunity evidence. |

First-slice acceptance rule:

`bad_fight_selection` may produce a mission only when the action is observable
and trackable by accepted metrics, for example reducing opening deaths while
maintaining ADR/KAST context. It must not prescribe exact angles, rotations,
economy calls or trade-quality conclusions.

## Diagnostic, Tracking And Guardrail Metrics

| Metric | Category | Usage in first slice | Required caveat / guardrail |
|---|---|---|---|
| `result` / `winrate` | Diagnostic | Outcome side of impact leak. | Needs accepted source/date/sample for trend claims. |
| `round_score` | Diagnostic | Round differential and score context. | Side-specific inference remains separate and lower confidence. |
| `kills`, `deaths` | Diagnostic/tracking | Basic activity and death-cost context. | Requires correct target player. |
| `kd_ratio` | Diagnostic | Impact context, not root cause. | Do not use alone for role/map diagnosis. |
| `adr` | Diagnostic/tracking | Impact pressure and mission guardrail. | Medium reliability; AI should warn when source/parser coverage is partial. |
| `entry_kills`, `entry_deaths` | Diagnostic/tracking | Core bad fight selection evidence. | Event order and target-player dependency must be visible. |
| `early_deaths` | Diagnostic context | Timing context only. | Approximate; timing anchors required; no fallback to `entry_deaths`. |
| `kast` | Guardrail/context | Prevent "less death" missions from becoming passive. | Approximate; warning metric, not sole hard evidence. |
| `utility_damage` | Diagnostic/tracking | Impact support context. | Medium reliability; parser attribution caveat. |
| `flash_assists`, `enemies_flashed` | Context | Utility support context. | Approximate; not proof of team impact. |
| `headshot_rate` | Context | Aim context only. | Not crosshair placement evidence. |
| `swing_score` | Context | Heuristic round-impact context. | Approximate; not sole hard evidence. |
| `trade_kills` | Guardrail only | Display/warning if present. | Low; suppressed for diagnosis/recommendation. |
| `traded_deaths` | Guardrail only | Should remain unavailable. | Suppressed. |
| `side_split_metrics` | Guardrail only | Display warning only. | Suppressed for diagnosis/recommendation. |
| `aim_rating`, `grenade_rating`, `crosshair_placement` | Guardrail only | Must remain data gaps. | Unavailable and suppressed. |

Mission tracking metrics for the first slice:

| Mission family | Primary tracking | Balance guardrail | Failure guardrail |
|---|---|---|---|
| Impact Leak | ADR, round result/window outcome, entry death count when relevant. | KAST and deaths remain caveated balance checks. | No "progress failed" unless metric confidence and sample/window policy pass. |
| Bad Fight Selection | Entry deaths per match or accepted opening-death opportunities. | ADR/KAST context to avoid passive play. | No hard failure from `early_deaths`, trade or side metrics. |

## AI Scout Contract

AI Scout is a candidate generator, not an acceptance authority.

Input:

| Field | Requirement |
|---|---|
| `contract_snapshot` | AI coach prompt/payload/metric registry versions when Scout uses AI payloads. |
| `domain_contract` | Same guardrails as current AI coach payload. |
| `metric_snapshots` | Values, confidence, source, sample and usage decision. |
| `derived_context` | Fight/round/opportunity facts with provenance and data gaps. |
| `active_recommendation` | Current accepted active recommendation context, currently recommendation `#5`. |
| `blocked_legacy_recommendations` | `[1, 3, 4]` unless future accepted refresh changes this. |

Output:

| Field | Requirement |
|---|---|
| `candidate_id` | Stable id or deterministic hash. |
| `problem_id` | `impact_leak`, `bad_fight_selection` or future registered problem id. |
| `title` | Short internal title, not final user advice. |
| `claim` | Bounded candidate claim. |
| `evidence_chain` | `problem -> metric -> match/window -> recommendation/mission`. |
| `evidence_metric_ids` | Registered ids only. |
| `metric_confidence` | Per evidence metric. |
| `sample` | Match/round/opportunity counts and omissions. |
| `confidence` | Cannot exceed weakest evidence link. |
| `caveats` | Required for warn/approximate/mixed-source/sparse evidence. |
| `proposed_card` | Draft insight card fields. |
| `proposed_mission` | Draft mission fields. |
| `guardrail_flags` | Known limitations and any blocked claim risks. |

## Evidence Validator Rules

Validator status values:

- `accepted`
- `accepted_with_warnings`
- `rejected`

Required deterministic checks:

| Rule | Reject when |
|---|---|
| Schema | Required fields or version metadata are missing. |
| Metric registry | Metric id is unknown. |
| Metric usage | Metric is suppressed or unavailable for the requested use. |
| Metric confidence | Evidence metric confidence is missing or overstated. |
| Weak evidence | Hard wording relies on `warn`, `low`, `approximate` or unavailable evidence without caveats. |
| Evidence chain | Problem, metric, match/window and recommendation/mission link is incomplete. |
| Source/sample | Sample/window/source policy is missing for pattern or trend claims. |
| Domain claims | Candidate claims exact playlist, public/friends readiness, v1.0, economy, positioning, clutch, crosshair placement, hard trade, exact match date without accepted source or unsupported parser data. |
| Recommendation policy | Candidate gives hard new evaluation to legacy recommendations `#1`, `#3` or `#4` without accepted refresh. |
| Actionability | Proposed mission cannot be tracked by accepted metrics. |

Safe fallback:

- Rejected Scout candidates may be logged as rejected diagnostic artifacts in a future explicitly scoped storage WP, but must not appear as accepted insight cards or coach advice.
- Rejection output must include issue codes, paths and a short remediation hint.

## Insight Card Storage Contract

This is a logical contract only. No schema change is authorized by MVP-005.

Required card fields:

| Field | Requirement |
|---|---|
| `card_id` | Stable id. |
| `card_version` | Version string, for example `insight-card-v1`. |
| `status` | `active`, `superseded`, `completed`, `rejected` or `archived`; only Validator-accepted cards can be `active`. |
| `problem_id` | Registered problem id. |
| `title` | User-facing short label. |
| `summary` | Caveated one-to-two sentence explanation. |
| `severity` | `low`, `medium` or `high`, bounded by evidence confidence. |
| `confidence` | `low`, `medium` or `high`, bounded by weakest evidence link. |
| `evidence` | Metric ids, values, confidence, match/window ids, sample and caveats. |
| `validator` | Status, issue codes and accepted/rejected timestamp. |
| `domain_guardrails` | Snapshot of applicable guardrails. |
| `source_refs` | Parser artifact ids, metric snapshot ids, payload hash or Scout candidate id. |
| `mission_id` | Nullable link to mission. |
| `created_at` / `updated_at` | UTC timestamps. |

Current storage note: `CoachReport.report_json` can store AI report metadata
today, but durable insight cards and missions need a future explicit DB/schema
WP if they are to become first-class stored objects.

## Mission And Checkpoint Contract

Mission fields:

| Field | Requirement |
|---|---|
| `mission_id` | Stable id. |
| `mission_version` | Version string, for example `mission-v1`. |
| `source_card_id` | Accepted insight card id. |
| `status` | `planned`, `active`, `paused`, `completed`, `failed`, `expired` or `archived`. |
| `objective` | Behavior/change statement bounded by evidence. |
| `tracking_window` | Match count or date window. First slice should prefer 5-10 future matches. |
| `primary_metrics` | Accepted tracking metric ids. |
| `balance_metrics` | Metrics that prevent harmful optimization, usually ADR/KAST/deaths caveated by confidence. |
| `success_rule` | Metric-aware rule with confidence and sample requirements. |
| `failure_rule` | Conservative rule; must not use weak metrics as hard failure. |
| `caveats` | Required evidence and data-gap caveats. |
| `created_from` | Scout candidate and Validator refs. |

Checkpoint fields:

| Field | Requirement |
|---|---|
| `checkpoint_id` | Stable id. |
| `mission_id` | Parent mission id. |
| `match_id` | Nullable until evaluated against a future accepted match. |
| `checkpoint_index` | Sequential number. |
| `metrics_snapshot` | Values and confidence at checkpoint. |
| `status` | `pending`, `green`, `yellow`, `red`, `gray` or `blocked`. |
| `coach_note` | Bounded, caveated feedback. |
| `validator_status` | Evaluation guardrail result. |

## Coach Output Requirements

Coach output may only use accepted insight cards and active mission state.

Required output fields:

- `summary`
- `main_focus`
- `why_this_matters`
- `evidence`
- `mission`
- `next_match_actions`
- `confidence`
- `caveats`
- `warnings`

Output rules:

- Always show confidence and caveats when evidence is not high-confidence.
- Never omit data gaps if they affect the advice.
- Do not present Scout candidates as accepted advice until Validator accepts them.
- Do not claim exact playlist/mode, public/friends readiness, `v1.0`, unsupported parser data or unavailable CS2 models.
- Do not convert weak metrics into completed/failed/progress claims.
- For no-data or rejected evidence paths, use safe fallback with visible validation issues.
- User-facing wording should be concrete but bounded, for example "In the next 5 matches, reduce opening deaths while keeping ADR from dropping", not "your positioning is bad".

## Recommended WP Sequence After MVP-005

Use the canonical mapping named in the task card. MVP IDs are runner bootstrap
ids only; future work should use these WP ids.

| WP ID | Title | Purpose |
|---|---|---|
| `WP-060` | Parser Artifact Contract Freeze | Freeze parser artifact envelope, confidence and data-gap requirements. |
| `WP-061` | Normalized Event Envelope Contract | Define normalized event schemas for rounds, player rounds, damage, duels, weapons and grenades. |
| `WP-062` | Parser Artifact To Normalized Event Fixtures | Add accepted/rejected sanitized fixtures for parser-to-event conversion without running live parser jobs. |
| `WP-063` | Derived Fight Context Contract | Define fight episode, opening duel, utility context and round context envelopes. |
| `WP-064` | Impact Leak Detector Contract | Implement/report the accepted `impact_leak` rules and fixtures. |
| `WP-065` | Bad Fight Selection Detector Contract | Implement/report the accepted `bad_fight_selection` rules and fixtures. |
| `WP-066` | Derived Context Guardrail Fixtures | Add fixtures for unsupported economy, positioning, clutch, crosshair, trade and playlist claims. |
| `WP-067` | Parser-To-Derived Acceptance Review | Review Phase 6 evidence and carry caveats forward. |
| `WP-070` | Metric Snapshot Contract | Define metric snapshot schema with source, sample, confidence and usage decision. |
| `WP-071` | Metric Snapshot Fixture Suite | Add golden accepted/rejected snapshots for first-slice metrics. |
| `WP-072` | Impact Leak Metric Snapshot Rules | Bind `impact_leak` to allowed metrics, sample thresholds and caveats. |
| `WP-073` | Bad Fight Selection Metric Snapshot Rules | Bind `bad_fight_selection` to allowed metrics, opportunity counts and caveats. |
| `WP-074` | Mission Tracking Metric Contract | Define primary, balance and failure-guardrail metrics. |
| `WP-075` | Metric Confidence Regression Gate | Extend tests so missing/overstated confidence blocks hard claims. |
| `WP-076` | Snapshot To Coach Payload Bridge | Feed metric snapshots into the AI coach payload without weakening current validator behavior. |
| `WP-077` | Metrics/Summaries Acceptance Review | Review Phase 7 and confirm weak-metric caveats. |
| `WP-080` | AI Scout Input Contract | Define Scout input envelope over derived context and metric snapshots. |
| `WP-081` | AI Scout Candidate Output Contract | Define candidate schema and accepted problem ids. |
| `WP-082` | Scout Fixture Suite | Add accepted/rejected Scout candidates for both first-slice domains. |
| `WP-083` | Evidence Validator Rule Set | Implement deterministic validation rules for Scout candidates. |
| `WP-084` | Evidence Validator Safe Fallback | Add rejected-candidate fallback and issue-code reporting. |
| `WP-085` | Scout-To-Validator Integration | Wire Scout candidates through Validator only, with no direct user-facing advice. |
| `WP-086` | AI Scout/Validator Acceptance Review | Review Phase 8 and preserve all output-quality guardrails. |
| `WP-090` | Insight Card Contract | Define durable card fields, statuses, evidence and caveat payloads. |
| `WP-091` | Insight Card Storage Plan | Plan DB/schema mutation for cards, with backup/SHA evidence if authorized. |
| `WP-092` | Mission Contract | Define mission lifecycle, tracking windows and checkpoint schema. |
| `WP-093` | Mission Storage Plan | Plan DB/schema mutation for missions/checkpoints, with backup/SHA evidence if authorized. |
| `WP-094` | Coach Output Contract | Define user-facing output fields and fallback behavior. |
| `WP-095` | Mission Evaluation Guardrails | Define future evaluation status logic without running evaluator/manual evaluator jobs unless authorized. |
| `WP-096` | Missions/Coach Output Acceptance Review | Review Phase 9 before UI integration. |
| `WP-100` | Coach UI Contract | Define personal UI surfaces for insight cards and missions. |
| `WP-101` | Insight Card UI Slice | Implement card display using accepted card payloads only. |
| `WP-102` | Mission UI Slice | Implement mission/checkpoint display and caveats. |
| `WP-103` | Coach Output UI Slice | Render final coach output with confidence and fallback states. |
| `WP-104` | End-To-End Fixture Path | Add parser-artifact-to-output fixture path without live import/parser/evaluator execution unless separately authorized. |
| `WP-105` | Owner-Only UX Guardrails | Preserve personal owner-only scope and public/friends blocked status. |
| `WP-106` | Personal MVP Vertical Slice Acceptance | Review the first end-to-end slice with carried warnings. |
| `WP-107` | Phase 10 Handoff And Next Lane Decision | Handoff accepted limitations and choose the next scoped lane. |

Immediate next task: `WP-060 Parser Artifact Contract Freeze`.

## Checks

- `git status --short` before work: clean.
- `git branch --show-current`: `cona`.
- Full tests: not run, per task card.
- Import/parser/evaluator/manual evaluator jobs: not run.
- DB/schema/data mutation: not performed.
- Service/deploy/runtime changes: not performed.
- Package/dependency changes: not performed.
- Git add/commit/push: not performed.
- `git diff --check` after writing report: passed.
- `git status --short` after writing report: only this new report file is
  untracked.

## Changed Files

- `docs/audit/MVP_005_AI_COACH_DATA_CONTRACT_VERTICAL_SLICE.md`

## Risks And Blockers

- `PASS_WITH_WARNINGS` rather than `PASS` because this is a contract/report
task only. The contract is not implemented, no storage schema exists for first
class insight cards or missions, and no end-to-end fixture yet proves the full
path.
- Existing rule-based mistake detection includes categories such as economy and
crosshair placement as no-data/data-gap concepts. Future WPs must ensure those
cannot become hard Scout candidates without new accepted evidence.
- Existing parser tables contain trade and side-related fields, but current
Metric Truth keeps hard trade, traded-death and side split claims suppressed.

## Safety Confirmations

- Report-only scope preserved.
- Public/friends readiness remains blocked.
- `v1.0` readiness is not claimed.
- Playlist/mode remains unknown or provenance-only.
- No unsupported coach/domain claims were accepted as implemented.
- No forbidden runtime, DB, data, service, dependency, raw demo or git side
effects were performed.
