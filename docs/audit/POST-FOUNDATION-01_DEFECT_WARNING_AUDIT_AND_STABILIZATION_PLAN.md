# POST-FOUNDATION-01 Defect / Warning Audit And Stabilization Plan

Task ID: `POST-FOUNDATION-01_DEFECT_WARNING_AUDIT_AND_STABILIZATION_PLAN`

Date: 2026-07-09

## Result

`PASS_WITH_WARNINGS`

The post-foundation blocker/warning state was reviewed without product,
runtime, DB, import, parser, evaluator, service, deploy or package changes.
No new runtime/product defect was found that requires broad remediation before
WP-018 planning can resume.

The current block on WP-018 is a control-plane/product-restart gate: Hot docs
require this post-foundation audit/stabilization lane and a later explicitly
authorized focused WP-018 restart task card before unrestricted WP-018 work.
This report satisfies the audit/planning artifact, but it does not itself set
`READY_FOR_MAJOR_CS2_FEATURE_WORK=YES`, start WP-018, claim `v1.0` or unlock
public/friends access.

## Branch / HEAD

- Branch: `cona`
- HEAD: `aa319c0316930a9982ee44c37a71f0667dfa35ab`
- Initial `git status --short`: clean, no output.

## Inputs Read

Hot docs:

- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/HANDOFF.md`
- `docs/project_management/WP_REGISTRY.md`
- `docs/project_management/PROMPT_PLAYBOOK.md`

Task-relevant Warm docs:

- `docs/TESTING.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/AI_COACH.md`
- `docs/RECOMMENDATIONS.md`
- `docs/METRICS.md`
- `docs/CS2_DOMAIN_CONTRACT.md`
- `docs/STEAM_IMPORT.md`
- `docs/foundation_hardening/2026-07-06-readiness-recovery-plan/RISK_REGISTER.md`

Targeted historical/closure evidence read because Hot docs explicitly reference
it for the current post-foundation blocker state:

- `docs/archive/lean-docs-2026-07-09/from-root/docs/foundation_hardening/2026-07-06-readiness-recovery-plan/task_reports/FH-125_128_final-foundation-closure-post-foundation-audit-handoff_report.md`

Broad docs, old task reports and unrelated archives were not read.

## Checks Run

Preflight:

- `git status --short`: exit `0`, no output.
- `git branch --show-current`: exit `0`, `cona`.
- `git rev-parse HEAD`: exit `0`,
  `aa319c0316930a9982ee44c37a71f0667dfa35ab`.

Docs/test safety checks:

- `.venv/bin/python scripts/project_gate.py preflight`: exit `0`.
- `.venv/bin/python scripts/project_gate.py required-checks`: exit `0`.
- `APP_ENV=test PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/bin/pytest tests -q -p no:cacheprovider`:
  exit `0`, `253 passed, 1 warning in 11.51s`.

The bare `timeout 300 pytest -q` form was not used because `docs/TESTING.md`
defines the safe full-suite form with `APP_ENV=test`, `PYTHONDONTWRITEBYTECODE=1`,
the repository venv and `-p no:cacheprovider`. The safe full-suite equivalent
was run under the requested 300 second timeout.

Final checks:

- `.venv/bin/python scripts/project_gate.py changed`: exit `0`; only the
  allowed new report was listed as untracked.
- `.venv/bin/python scripts/project_gate.py postflight`: exit `0`; only the
  allowed new report was listed as untracked; production DB SHA observed
  read-only and unchanged from preflight evidence.
- `git diff --check`: exit `0`, no output.
- `git status --short`: exit `0`; only
  `?? docs/audit/POST-FOUNDATION-01_DEFECT_WARNING_AUDIT_AND_STABILIZATION_PLAN.md`.

## Readiness Summary

Current state:

- Foundation hardening is closed only as
  `FOUNDATION_HARDENING_CLOSED_PENDING_POST_FOUNDATION_AUDIT`.
- `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`.
- WP-018 is planned/paused pending post-foundation audit and stabilization plus
  a later explicitly authorized restart task card.
- `v0.9` is promoted with warnings by WP-017K.
- System `v1.0` is not claimed.
- Public/friends readiness remains blocked.

Already closed and should not keep blocking WP-018 planning:

- H1 final-readiness rerun evidence was accepted by FH-124R-03/H2:
  full safe pytest passed, local quality gate passed and project gate checks
  passed, with one non-blocking upstream `TestClient` deprecation warning.
- Foundation P0/P1 design and contract work is mostly closed or accepted as
  visible restriction. In particular, diagnosis/planner design, Metric Truth,
  source trust, sample thresholds, AI advice confidence, evidence links and
  CS2 domain boundaries are documented.
- WP-017I/WP-017J resolved the match-mode promotion blocker by accepting an
  explicit v0.9 deferral; exact playlist mode remains unavailable, but that is
  a warning/guardrail, not an unresolved v0.9 promotion blocker.

Current WP-018 blockers:

- A later explicit WP-018 restart task card is still required. This audit does
  not authorize implementation by itself.
- Unsupported coach/domain claims remain blocked. WP-018 may calibrate quality
  and caveats, but must not expand into unsupported planner, economy,
  positioning, clutch, exact playlist/mode, public/friends or v1.0 claims.
- Schema-changing work remains blocked unless separately authorized behind
  migration/DB safety scope. This matters only if a future WP-018 task proposes
  runtime persistence/schema changes.

Current warnings that can carry into a narrow WP-018 restart:

- Upstream Starlette/httpx `TestClient` deprecation warning in the safe pytest
  suite.
- Hosted CI/branch protection is not configured; local gate is the accepted
  current discipline.
- API contract/live ASGI depth and owner/auth edge coverage are accepted
  personal-lane limitations.
- Prompt/payload version tracking and metric-registry/prompt-payload runtime
  snapshots are not implemented.
- Provider-specific structured response enforcement and semantic entailment
  checks remain future AI coach hardening.
- Steam import remains one-demo-capped with durable worker/retry/cap-raise work
  deferred.
- Playlist/mode, weak metrics, side/trade/economy/positioning/clutch and
  source/sample-size caveats must remain visible.

## Product Guardrails

- WP-018 paused: preserved.
- Public/friends blocked: preserved.
- `v1.0` not claimed: preserved.
- Recommendation `#5` active: preserved as the only accepted active hard
  recommendation, with three evaluations and `metric_confidence`.
- Weak metrics caveated: preserved by Metric Truth, AI Coach, Recommendation
  and CS2 Domain contracts.
- Steam import cap remains `1`: preserved.
- Playlist/mode caveats preserved: exact Premier, Competitive, Wingman, Casual,
  Deathmatch, FACEIT and custom labels remain unsupported for `v0.9`.

## Warning / Defect Table

| item | source | severity | blocks WP-018 | recommended action | suggested next task ID |
|---|---|---:|---|---|---|
| WP-018 restart requires explicit authorization after this lane | `CURRENT_STATUS.md`, `HANDOFF.md`, `WP_REGISTRY.md`, FH-125_128 report | P1 | yes | Create a focused restart/scope-lock task card that carries warnings forward and names allowed WP-018 files/checks. | `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK` |
| `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO` | `CURRENT_STATUS.md`, `WP_REGISTRY.md`, FH-125_128 report | P1 | yes for major expansion; no for narrow scoped calibration | Do not flip globally for WP-018. Permit only narrow coach calibration tasks with explicit scope and guardrails. | `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK` |
| No migration engine / schema-changing work hard-blocked | `RISK_REGISTER.md` `R-FH-P0-001`, `CURRENT_STATUS.md` | P1 | no unless WP-018 wants schema/persistence changes | Keep WP-018 restart no-schema by default, or split schema work into a separate authorized DB/migration task. | `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK` |
| Public/friends access blocked | `CURRENT_STATUS.md`, `KNOWN_LIMITATIONS.md`, `RISK_REGISTER.md` `R-FH-P0-002` | P1 | no | Carry as release guardrail; do not mix with WP-018 coach quality. | none |
| Prompt/payload version tracking not implemented | `AI_COACH.md`, `RISK_REGISTER.md` `R-FH-P1-016` | P2 | no for restart; yes before treating new AI advice as accepted versioned evidence | Make WP-018 first implementation slice add no-schema prompt/payload/metric-registry version metadata if it will persist accepted advice. | `PF-STAB-02_AI_COACH_VERSIONING_AND_SNAPSHOT_NO_SCHEMA_SLICE` |
| Runtime metric-registry / prompt-payload snapshots not generated | `AI_COACH.md`, `RISK_REGISTER.md` `R-FH-P1-027` | P2 | no for restart; yes for stronger reproducibility claims | Keep as can-carry unless WP-018 needs accepted reproducible AI evidence; then implement no-schema snapshot path or explicitly defer. | `PF-STAB-02_AI_COACH_VERSIONING_AND_SNAPSHOT_NO_SCHEMA_SLICE` |
| Provider-specific structured response enforcement is shallow | `AI_COACH.md`, `KNOWN_LIMITATIONS.md` | P2 | no | Keep validator fallback behavior; scope richer provider enforcement after versioning/snapshot work. | `WP018-CAL-02_PROVIDER_STRUCTURE_AND_VALIDATOR_HARDENING` |
| Recommendation planner runtime not implemented | `RECOMMENDATIONS.md`, `AI_COACH.md`, `RISK_REGISTER.md` `R-FH-P0-003` | P2 | no for calibration; yes for planner-backed primary recommendation | Do not implement planner in the restart task. Preserve active recommendation `#5`; treat planner as a later explicit WP-018 slice. | `WP018-CAL-03_DIAGNOSIS_PLANNER_IMPLEMENTATION_ENTRY_REVIEW` |
| Weak metrics can overclaim if caveats are lost | `METRICS.md`, `AI_COACH.md`, `RECOMMENDATIONS.md`, `CS2_DOMAIN_CONTRACT.md` | P1 | no if guardrails remain enforced | Include caveat/claim review and semantic eval checks in every WP-018 coach-output task. | `PF-STAB-03_WP018_CLAIM_CAVEAT_TEST_MATRIX` |
| Exact playlist/mode unavailable | `CURRENT_STATUS.md`, `WP_REGISTRY.md`, `CS2_DOMAIN_CONTRACT.md`, `METRICS.md` | P2 | no | Carry limitation. WP-018 must not create playlist-specific advice, filters or claims. | `PF-STAB-03_WP018_CLAIM_CAVEAT_TEST_MATRIX` |
| Side/trade/economy/positioning/clutch unavailable or display-only | `CS2_DOMAIN_CONTRACT.md`, `METRICS.md`, `AI_COACH.md` | P2 | no | Carry limitation. Use suppression/caveat tests for coach output if touched. | `PF-STAB-03_WP018_CLAIM_CAVEAT_TEST_MATRIX` |
| Steam import cap remains `1`; durable worker/retry/cap raise deferred | `AGENTS.md`, `CURRENT_STATUS.md`, `STEAM_IMPORT.md`, `RISK_REGISTER.md` | P2 | no | Keep out of WP-018. Do not run imports or raise cap. | none |
| Historical queued non-parent Steam jobs `#1` and `#10` remain | `CURRENT_STATUS.md` | P3 | no | Carry as import/admin warning; do not remediate during WP-018 unless a future import/admin task scopes it. | none |
| `/coach` artifact overview should be optimized before materially larger demo volume | `CURRENT_STATUS.md`, `KNOWN_LIMITATIONS.md` | P3 | no | Carry until volume grows or UI performance work is scoped. | none |
| Authenticated owner-browser timing not captured by Codex evidence | `CURRENT_STATUS.md`, `KNOWN_LIMITATIONS.md` | P3 | no | Carry; collect only if a future UI/performance task scopes browser evidence. | none |
| Hosted CI/branch protection not configured | `TESTING.md`, `RISK_REGISTER.md` `R-FH-P1-003`, `R-FH-P1-029` | P2 | no | Continue local quality gate discipline; hosted CI remains future policy. | none |
| API contract/live ASGI validation depth accepted as limited | `RISK_REGISTER.md` `R-FH-P1-005` | P2 | no | Add targeted contract tests only when WP-018 changes endpoints or response contracts. | `PF-STAB-03_WP018_CLAIM_CAVEAT_TEST_MATRIX` |
| Owner/auth edge coverage accepted as personal-lane limitation | `RISK_REGISTER.md` `R-FH-P1-006`, `KNOWN_LIMITATIONS.md` | P2 | no | Carry public-readiness block; do not expand access. | none |
| Upstream Starlette/httpx `TestClient` deprecation warning | Safe pytest run, FH-125_128 report | P3 | no | Track as non-blocking dependency warning; do not install/change packages without explicit package scope. | none |

## Must-fix Before WP-018

1. `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK`
   - Produce the explicit WP-018 restart/scope-lock task card.
   - Keep `READY_FOR_MAJOR_CS2_FEATURE_WORK=NO` globally unless a future
     source-of-truth update explicitly changes it.
   - Authorize only narrow coach calibration, caveat, prompt/versioning, test
     or documentation work.
   - Forbid schema/DB/import/parser/evaluator/service/deploy/package changes
     unless separately scoped.
   - Carry active recommendation `#5`, weak-metric caveats, playlist/mode
     deferral and public/friends block into the task card.

No broad product/runtime fix is required before drafting that restart task.

## Can-carry Warnings

- `v0.9` is promoted with warnings, not a v1.0/public release.
- Local gate is accepted; hosted CI/branch protection remains future policy.
- Upstream `TestClient` deprecation warning remains non-blocking.
- Prompt/payload versioning and runtime snapshots are can-carry only if WP-018
  does not treat new AI advice as accepted versioned evidence.
- Provider-specific structured response mode and semantic entailment checks are
  future hardening.
- API/live ASGI depth and owner/auth edge coverage remain accepted personal-lane
  limitations.
- Steam import remains alpha, cap remains `1`, and worker/retry/cap raise work
  stays outside WP-018.
- Raw demos and backups remain on root-backed storage; no storage cleanup is
  authorized here.
- `/coach` artifact overview optimization is deferred until materially larger
  demo volume or scoped UI/performance work.
- Authenticated owner-browser timing evidence remains uncaptured.

## Deferred Items

- Public/friends readiness and social/sharing access.
- System `v1.0` claim.
- Import cap raise, durable worker, retry ledger and larger Steam batches.
- Migration engine / production migration capability.
- Recommendation planner runtime implementation, unless explicitly selected as
  a later WP-018 slice after entry criteria review.
- Parser hardening for side switching, trade windows, traded deaths, economy,
  positioning, clutch and canonical map registry.
- FACEIT, viewer, heatmaps, clips, payments and social features.

## Recommended Next Task

`PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK`

Purpose: turn this audit result into a focused WP-018 restart task card without
starting implementation. The task should lock scope to coach quality
calibration and safety checks, preserve all v0.9 warnings, and explicitly
decide whether the first WP-018 slice is:

1. claim/caveat test matrix and semantic fixture review;
2. no-schema AI prompt/payload/version metadata; or
3. narrow coach output wording calibration around recommendation `#5`.

Recommended 3-5 task stabilization sequence:

1. `PF-STAB-01_WP018_RESTART_AUTHORIZATION_AND_SCOPE_LOCK`
2. `PF-STAB-03_WP018_CLAIM_CAVEAT_TEST_MATRIX`
3. `PF-STAB-02_AI_COACH_VERSIONING_AND_SNAPSHOT_NO_SCHEMA_SLICE`
4. `WP018-CAL-01_RECOMMENDATION_5_COACH_OUTPUT_CALIBRATION`
5. `WP018-CAL-02_PROVIDER_STRUCTURE_AND_VALIDATOR_HARDENING`

## Safety Notes

- No files outside this report were intentionally changed.
- No DB/schema/data/import/parser/evaluator/manual evaluator work ran.
- No live Steam/Valve import ran.
- No service restart, deploy command, package install, commit or push ran.
- The production DB SHA was observed read-only by project-gate preflight as
  `2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33`.
- This report is a planning artifact only. It does not start WP-018 or change
  product/runtime behavior.
