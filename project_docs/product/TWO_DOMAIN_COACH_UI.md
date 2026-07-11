# Two-Domain Coach UI Contract

The Product coach workspace has exactly two fixed positions, in this order:
`impact_leak` (Impact Leak / Useful Impact / Unconverted Impact) and
`bad_fight_selection` (Bad Fight Selection / Fight Selection / Duel
Discipline). Performance, utility, and aim remain metric groups, never cards.

The owner-scoped web composition boundary consumes `coach-domain-slots-v1`,
mission/progress serializers, safe match summaries, and locale helpers. Routes
do not reconstruct mission semantics; templates do not query persistence. A
page GET never activates a mission or starts Steam, parser, evaluator, metric,
or model work.

## State and action behavior

- `insufficient_baseline` and accepted `insufficient_evidence` explain that
  data is insufficient and offer no activation.
- `analyzing` is read-only and does not imply that page load started analysis.
- `proposal_ready` is not active and exposes one explicit, owner-authenticated,
  CSRF-protected activation action for the current matching proposal.
- `active` identifies the mission and shows post-activation progress only.
- progress `insufficient_data` is not failure; sample and minimum are shown.
- `no_material_problem` offers no mission.
- `analysis_failed` and unavailable composition are visible safe errors, never
  empty cards or raw exceptions.
- superseded/noncurrent proposals are stale and cannot be activated.
- paused/completed lifecycle states remain non-actionable in this MVP.

Activation reuses the canonical proposal activation service. It verifies
owner, domain, current slot and proposal, is idempotent, and uses
Post/Redirect/Get. Each domain is independent: one, both, or neither may be
active; page views never autoactivate.

## Content and progress

Cards show supported headline, hypothesis, primary pattern, focus, confidence
and rationale, evidence, counterevidence, caveats, baseline window, target
metric, baseline/current/target values, mission lifecycle, sample/minimum,
latest result and recent history when present. Shared metrics do not merge
diagnoses: each card keeps its own hypothesis and behavioral focus.

No synthetic percentage is shown. Progress uses the persisted sample count and
baseline/current/target comparison. Matches in the activation baseline are
explicitly not counted. A post-activation match is marked included only when a
persisted owner-scoped progress evaluation contains its match id.

Match detail has one row per canonical domain with evaluation state, match
value, baseline, target, inclusion, human-readable limitations, confidence and
caveats. Missing evaluation, pre-activation, insufficient-data, failure and
unavailable states remain distinct. Another owner's match is not visible.

The dashboard contains only two-domain state/progress navigation. Historical
recommendations, manual AI/report actions, and technical sync remain collapsed
and explicitly noncanonical. Internal IDs and reason codes may appear only in
collapsed technical details; secrets, paths, prompts, raw responses, ORM
representations, and raw exceptions never appear.
