# Layer Readiness

## Layer 1. Agentic Development Core - 4.0/5

Strongest layer. `AGENTS.md`, Hot/Warm/Cold protocol, WP registry, role cards, invocation modes, output modes and control-plane protection are coherent. The main weakness is enforcement: most rules are human/agent policy, with only partial scripting in `scripts/project_gate.py` and no CI.

## Layer 2. Web Application Core - 3.0/5

The app is usable for controlled personal/VPS operation: FastAPI, Jinja, SQLAlchemy, SQLite, auth/session/CSRF/rate limits and tests exist. The blocking weakness is schema/change management: no Alembic baseline, legacy startup schema upgrade remains, and BackgroundTasks are not a durable worker architecture.

## Layer 3. AI Coach Product Archetype - 3.1/5

Recommendation tracking, metric confidence and AI validation are real. However, the product lacks the next foundational coach layer: diagnosis registry, top verified problem selection, planner, prompt/payload versioning and semantic AI evals.

## Layer 4. CS2 Domain Pack - 2.9/5

The project is honest about weak CS2 facts. Match/round/parser artifact models exist, and Metric Truth suppresses unsafe claims. But economy, positioning, clutch definitions, canonical map registry, sample-size policy and CS2 glossary are missing or incomplete.

## Layer 5. Project Instance - 3.5/5

Current stack, state, roadmap, acceptance and limitations are clear. Historical docs and runtime artifacts create noise, but DOCS_INDEX/DOCS_MAP reduce the risk. The instance is manageable if agents respect source-of-truth order.

## Layer 6. Runtime Layer - 4.1/5

This audit was executed with clear scope, evidence files, safe tests and no production mutation. Runtime discipline is good for file-backed audits and WPs. It is still mostly manual outside the current execution.
