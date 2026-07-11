# WP-017R Roadmap / WP Registry Governance Repair Report

Date: 2026-07-05

## RESULT: REPAIRED

WP-017 roadmap/WP registry governance was repaired. A canonical WP registry was
created, current roadmap/status docs were aligned to it, and a compact project
gate check now reports whether `AGENTS.md` and the WP registry exist.

This WP did not promote `v0.9`.

## Drift Found

Numbering drift was present in the WP-017 lane:

- match mode classification diagnosis/repair had been planned for WP-017;
- emergency repair WPs were inserted because the Steam-path automatic
  recommendation evaluation trigger became a blocker;
- the documents then pointed `WP-017I` directly at `v0.9` promotion;
- match mode WPs remained open and were not explicitly completed, deferred or
  superseded.

The old history was preserved. No historical WP-017 audit report was deleted or
renamed.

## Canonical WP-017 Order

Done:

- `WP-017A` Real Data Onboarding / Bulk Demo Usage Diagnosis.
- `WP-017B` Controlled Bulk Import Plan / Guard Settings.
- `WP-017C` First Controlled Bulk Import Batch / No-New Path.
- `WP-017C2` Controlled Import After New Match / One-Demo Batch-Cap Path.
- `WP-017D` Post-Batch Acceptance + Auto-Evaluation Trigger Diagnosis.
- `WP-017E` Auto-Evaluation Trigger Repair for Steam Batch Import Path.
- `WP-017F` Controlled Pending Share Code `#73` Import.
- `WP-017G` Post-Batch Data Integrity Acceptance.
- `WP-017H` Post-Batch Performance Acceptance.
- `WP-017I0` Add Root `AGENTS.md` Project Contract.

Current:

- `WP-017R` Roadmap / WP Registry Governance Repair.

Planned:

- `WP-017I` Match Mode Classification Diagnosis.
- `WP-017J` Match Mode Classification Repair / Labels, if recoverable, or
  explicit deferral.
- `WP-017K` Real Data Onboarding Promotion to `v0.9`.

## Governance Gate

Automated compact project gate was updated:

- `python3 scripts/project_gate.py preflight` reports whether `AGENTS.md` exists.
- `python3 scripts/project_gate.py preflight` reports whether
  `docs/project_management/WP_REGISTRY.md` exists.
- `python3 scripts/project_gate.py postflight` reports both files again.

Manual governance gate was also documented:

- `AGENTS.md` must exist.
- `docs/project_management/WP_REGISTRY.md` must exist.
- Promotion WPs must verify registry prerequisites.
- WP IDs must not be silently reused.
- If a planned WP is skipped, it must be marked `deferred` or `superseded` with
  reason.
- `v0.9` promotion is blocked until `WP-017I` and `WP-017J` are completed or
  explicitly deferred with documented accepted limitation.

## Files Changed

- `docs/project_management/WP_REGISTRY.md` created.
- `docs/CURRENT_STATUS.md` updated to identify `WP-017R` as current and record
  the promotion blocker.
- `docs/HANDOFF.md` updated with the registry order and next WP.
- `docs/PROJECT_CONTROL.md` updated with registry source of truth and governance
  gate rules.
- `docs/project_management/WORK_PACKAGE_BACKLOG.md` updated with `WP-017I0`,
  `WP-017R`, `WP-017I`, `WP-017J` and `WP-017K`.
- `docs/project_management/ACCEPTANCE_MATRIX.md` updated to block `v0.9`
  promotion until match mode WPs are resolved.
- `docs/project_management/VERSION_ROADMAP.md` updated to use
  `WP-017A`-`WP-017K`.
- `scripts/project_gate.py` updated with compact read-only governance file
  presence checks.
- `docs/audit/WP_017R_ROADMAP_WP_REGISTRY_GOVERNANCE_REPAIR_REPORT.md`
  created.

## Registry Presence

| Item | Status |
|---|---|
| `AGENTS.md` exists | yes |
| `docs/project_management/WP_REGISTRY.md` exists | yes |
| project gate changed | yes |
| manual gate documented | yes |

## Whether v0.9 Promotion Is Allowed Now

No.

Promotion is blocked until:

- `WP-017I` Match Mode Classification Diagnosis is completed;
- `WP-017J` Match Mode Classification Repair / Labels is completed, or mode
  classification is explicitly deferred with a documented accepted limitation;
- `WP-017K` verifies registry prerequisites and makes the promotion/block
  decision.

## DB SHA

Before work:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

After work:

```text
2f7a712a4505b43c25a7e6b32b90f69102789362026d650f7a8b18f6650d1e33  data/cs2_coach.db
```

DB SHA unchanged: yes.

## Verification

Initial required commands were run:

```text
git status --short
git log --oneline -30 --decorate
sha256sum data/cs2_coach.db
python3 scripts/project_gate.py preflight
python3 scripts/project_gate.py changed
python3 scripts/project_gate.py required-checks
```

Final required commands were run:

```text
python3 -m py_compile scripts/project_gate.py
git diff --check
python3 scripts/project_gate.py postflight
sha256sum data/cs2_coach.db
```

## Safety Declarations

| Item | Status |
|---|---|
| production DB touched | no |
| production files touched | no |
| live import/parser run | no |
| live Steam/Valve import run | no |
| demo download run | no |
| manual evaluator run | no |
| persistent app report generated | no |
| schema changed | no |
| cap changed | no |
| raw demos deleted/moved/compressed | no |
| runtime/product code changed | no |
| recommendation/import/parser logic changed | no |
| tests changed | no |
| commit made | no |

## Blockers

None for WP-017R.

## Next Required WP

`WP-017I Match Mode Classification Diagnosis`.
