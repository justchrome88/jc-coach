# GATE-001 MVP Development Stop-Signal Review

Scope: diagnostic-only review of stop-signals and authorization gates for auth, Steam identity, import, demo storage, parser, DB/schema/data, evaluator/AI coach, automation/runner behavior, and major CS2/WP-018 constraints.

## Required Checks

- `git branch --show-current`: `cona`
- `git status --short`: clean (no changes before report creation)

## Verdict

**NEEDS_USER_DECISION**  
Core safety gates are coherent but still active and not yet broad enough for unrestricted MVP implementation. Several gates can be relaxed only after explicit user-approved WP scope and evidence conditions.

## Stop-Signal Table

| Domain | Rule | Evidence (Origin) | Why it exists | Classification |
|---|---|---|---|---|
| Readiness/roadmap | `READY_FOR_MAJOR_CS2_FEATURE_WORK` remains `NO`; major WP-018/CS2 expansion paused | `AGENTS.md:87-88`; `CURRENT_STATUS.md:48-56`; `WP_REGISTRY.md:122-123`; `WORK_PACKAGE_BACKLOG.md:10-15` | Prevents broad feature expansion before final readiness gate and explicit lane restart. | **REQUIRES_USER_DECISION** |
| Auth / Steam identity | Personal/VPS-only use remains current truth; friends/public readiness blocked | `SECURITY.md:7-15`, `AGENTS.md:88-89`, `CURRENT_STATUS.md:133` | Keeps identity and platform exposure within verified owner-only scope and avoids unsupported public model obligations. | **HARD_SAFETY_KEEP** |
| Auth / Steam identity | Single-owner policy is first active credentialed user as owner; registration closure behavior after owner exists; Steam callback requires owner session before linking and does not launch Steam/import jobs | `SECURITY.md:11`, `SECURITY.md:157-159`, `SECURITY.md:158-159` | Prevents accidental account takeover and unscoped side-effect work. | **HARD_SAFETY_KEEP** |
| Auth / evaluator | Legacy recommendations `#1`, `#3`, `#4` are blocked from new hard evaluations | `AGENTS.md:79`, `CURRENT_STATUS.md:130`, `HANDOFF.md:87` | Prevents unsupported recommender hard-claim rewrites without dedicated refresh evidence. | **HARD_SAFETY_KEEP** |
| Production DB / data | Production DB/schema/data mutation requires explicit authorization + backup + SHA evidence | `AGENTS.md:45-50`; `AGENTS.md:123-124`; `MIGRATIONS.md:26-37`; `DB_GUARDIAN.md:18-23`, `18`; `PROJECT_OPERATING_PROTOCOL.md:106-108` | Core anti-corruption rule for production persistence safety. | **HARD_SAFETY_KEEP** |
| Production DB / schema | Read-only DB inspection does not authorize schema migration, copied-DB work, startup-behavior change, or production mutation | `MIGRATIONS.md:30-37`, `MIGRATIONS.md:331-335`, `AGENT_WORKFLOW.md:331-335` | Prevents implicit privilege creep from inspection into mutation work. | **HARD_SAFETY_KEEP** |
| Import / parser / evaluator | Live import, parser, evaluator, or manual evaluator jobs require explicit user authorization | `AGENTS.md:49-50`; `CURRENT_STATUS.md:137-140`; `TESTING.md:119-124`; `AGENT_WORKFLOW.md:350-356`, `AGENT_WORKFLOW.md:559-560` | Prevents uncontrolled production jobs, stale state, and storage/db impact without scoped approval. | **HARD_SAFETY_KEEP** |
| Import / cap | `STEAM_IMPORT_MAX_DEMOS_PER_RUN` remains `1`; cap raise blocked without explicit cap-change WP | `AGENTS.md:81`; `CURRENT_STATUS.md:76,126`; `STEAM_IMPORT.md:70-74`; `ACCEPTANCE_MATRIX.md:16` | Prevents unbounded downloader/parser exposure and storage pressure while worker/retry safety is incomplete. | **TEMPORARY_GATE_CAN_RELAX** |
| Import / parser | Parser runs on production import/data remain explicit-risk work and require authorization | `ARCHITECTURE.md:320-321`, `ARCHITECTURE.md:413-414`, `TESTING.md:232-233` | Parser has already shown fragile points around schema/model compatibility; production execution must stay scoped. | **TEMPORARY_GATE_CAN_RELAX** |
| Demo storage | Raw demo delete/move/compress forbidden unless explicit storage WP; current policy is retain-by-default with status metadata | `AGENTS.md:55-56`; `IMPORT_GUARDIAN.md:36`; `CURRENT_STATUS.md:132`; `STEAM_IMPORT.md:33`, `81-83` | Preserves debuggability and prevents destructive data loss while parser/storage retention policy is incomplete. | **HARD_SAFETY_KEEP** |
| Demo storage policy | Raw demo deletion mode (`delete_after_success`) remains disabled by default; delete-after-success disabled remains future mode | `STEAM_IMPORT.md:34`, `STEAM_IMPORT.md:99-101`; `DEMO_STORAGE_TZ.md:20-23`, `31-33` | Keeps retention safety while parser + analytics completeness is still maturing. | **TEMPORARY_GATE_CAN_RELAX** |
| Evaluation / coaching | AI/coach and evaluator paths must keep evidence chains and confidence gating; unsupported hard advice is blocked | `AI_COACH.md:42-49`, `AI_COACH.md:56-69`, `AI_COACH.md:92-97`; `ACCEPTANCE_MATRIX.md:21` | Prevents confidence inflation and unsafe hard claims in recommendation loop. | **HARD_SAFETY_KEEP** |
| Service/runtime | Service/deploy/runtime changes require explicit scope; no service restart/deploy/config changes in this lane | `AGENTS.md:49-53`, `AGENTS.md:51-52`; `AGENT_WORKFLOW.md:358-363`; `CURRENT_STATUS.md:140` | Protects stability and avoids unreviewed runtime drift. | **HARD_SAFETY_KEEP** |
| Testing / isolation | Tests must be `APP_ENV=test` and never target production DB; live jobs prohibited in doc-only/testing defaults | `TESTING.md:7-10`, `TESTING.md:209-216`, `TEST_GUARDIAN.md:15-20` | Avoids silent contamination of production DB through test execution. | **HARD_SAFETY_KEEP** |
| Automation / runner | No scheduler/autonomous daemon/automation is part of current agent model; durable import-worker/retry/queue/stale-repair requires explicit runner/task scope | `AGENT_WORKFLOW.md:9-21`; `ARCHITECTURE.md:330-333`; `AGENT_WORKFLOW.md:585-590` | Prevents implicit infrastructure additions that would alter execution guarantees and recovery behavior. | **REQUIRES_USER_DECISION** |
| Stale/historical doc risk | `DEMO_STORAGE_TZ.md` is explicitly marked as supporting/historical (not current source) | `DEMO_STORAGE_TZ.md:1-10` | Indicates partial divergence risk with current canonical docs and requires one-line reconciliation in any storage-policy decision. | **STALE_OR_NEEDS_REVIEW** |
| Control-plane governance | Control-plane docs (including source-of-truth docs) can only be updated by explicit governance scope | `PROJECT_OPERATING_PROTOCOL.md:71-79`; `AGENT_WORKFLOW.md:167-193`; `WP_REGISTRY.md:14-20` | Prevents bypassing canonical state governance while changing product risk posture. | **HARD_SAFETY_KEEP** |

## Required conditions before authorizing full MVP implementation work

1. **Gate posture upgrade**: readiness decision (`READY_FOR_MAJOR_CS2_FEATURE_WORK`) and any blocking status flags in `CURRENT_STATUS.md`/`WP_REGISTRY.md` must be explicitly advanced by approved WP.  
2. **Scoped authorization per risk class**: each domain change (auth, DB/schema/data, import/parser/evaluator, storage, automation) must have an explicit WP card with allowed files, scope, and stop-condition acceptance.  
3. **Mutation evidence contract**: for every DB/mutation/runner/evaluator-cap change task, require explicit pre/post `sha256sum data/cs2_coach.db`, backup path (if mutation authorized), `project_gate.py` preflight/required-checks/postflight, and a written import-safety declaration.  
4. **Route/job safety gates for any enabled import/evaluation path**: cap/tempdir/storage checks, worker/runner behavior, retryability, and stale-job handling must be revalidated before scaling any live runner semantics.  
5. **Identity/risk containment remains intact**: owner/session boundary and non-public stance must remain in effect unless a later explicit public-readiness task provides an approved alternative.  

## Minimum restrictions to relax now (if user decides to proceed)

- `STEAM_IMPORT_MAX_DEMOS_PER_RUN` can be relaxed only after an explicit cap-change WP that includes worker/retry/result safety.  
- Raw-demo delete lifecycle (`delete_after_success`) can move forward only after parser completeness + retention policy verification and a storage retention WP.  
- Durable import worker/retry/queue/runners can be introduced only under an explicit runner/automation WP with explicit idempotency, lease, and stale-repair evidence.  
- Friendly/public readiness can only be relaxed via explicit security/public-readiness WP with full evidence package in `SECURITY.md` scope.  

## Restrictions that must remain until explicit user decision

- No production DB/schema mutation without explicit authorization, backup, and DB SHA evidence.  
- No production import/parser/evaluator/manual-evaluator jobs without explicit authorization and safety evidence.  
- No raw-demo delete/move/compress without storage WP scope.  
- No new hard recommendations/evaluator claims from weak or legacy recommendation IDs without explicit refresh acceptance.  
- No major WP-018/CS2 expansion while readiness remains `NO` and lane remains paused.  

## Which docs should change for a new MVP implementation lane

At minimum, update canonical status docs before opening the lane:

- `docs/CURRENT_STATUS.md` (readiness flag, active WP, gating summary)
- `docs/project_management/WP_REGISTRY.md` (active/reported WP status, especially WP-018 sequence transitions)
- `docs/HANDOFF.md` (next safe step and active lane note)
- `docs/project_management/WORK_PACKAGE_BACKLOG.md` (if WP order or acceptance packaging shifts)
- `docs/project_management/ACCEPTANCE_MATRIX.md` (if evaluator/coach/evidence acceptance criteria are changed)
- `docs/project_management/MASTER_WP_CHECKLIST.md` or `VERSION_ROADMAP.md` if campaign sequencing changes.

## Proposed next 5 WPs

Given current canonical sequence and active constraints:

1. `WP-018A_COACH_OUTPUT_QUALITY_DIAGNOSIS`
2. `WP-018B` Recommendation Category Quality Review
3. `WP-018C` Survival Recommendation Calibration
4. `WP-018D` Aim Recommendation Calibration
5. `WP-018E` Utility / Grenade Recommendation Calibration

## Final `git status --short`

After review report creation (before any implementation edits):

```
A  docs/audit/GATE_001_MVP_DEVELOPMENT_STOP_SIGNAL_REVIEW.md
```
