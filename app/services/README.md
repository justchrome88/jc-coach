# Service package map

JC Coach uses shallow bounded service packages:

- `ingestion/`: Steam discovery/history, demo acquisition, import jobs,
  retained storage, and canonical Steam match metadata.
- `parsing/`: DEM parsing, normalized events, artifact reads, and parser
  evidence validation.
- `metrics/`: metric computation, snapshots, confidence, analytics, and the
  legacy metric-recommendation evaluator.
- `coach/`: evidence bundles, the single provider boundary, structured-output
  validation, deterministic insights, reports, and two-domain proposals.
- `missions/`: payload validation, repositories, activation/lifecycle,
  progress evaluation, rolling candidates, and result serialization.
- `owner/`: identity/scope, auth/security, post-parser application
  orchestration, and owner-sync discovery/classification/execution.
- `shared/`: immutable primitives genuinely used by multiple packages.

Dependency direction is:

```text
app/contracts + app/db + shared
             -> ingestion -> parsing -> metrics -> coach -> missions

owner orchestration may coordinate all lower packages
API routes call public service entrypoints and serialize results
```

Public entrypoints are the non-private functions in the owning module. Package
`__init__.py` files do not hide implementations behind broad facades. The
logic-free root compatibility facades are listed by
`scripts/architecture_guardrails.py`; they remain only for established import
paths and are removed when their recorded callers or fixed-path contracts are
migrated. `coach_domain_model.py` is the approved root runtime contract loader.

Runtime JSON, schema, and prompt contracts live under `app/contracts/`.
Historical and narrative material is never imported by runtime code.
