# Testing

Last updated: 2026-07-03.

## Safe Commands

```bash
pytest
ruff check .
```

## Rules

- Do not run parser jobs, Steam jobs or import jobs during documentation-only tasks.
- Tests must not use production DB/settings.
- For Python route/template changes, perform live smoke checks only when the task explicitly involves runtime behavior and it is safe to start/restart the app.

## Coverage Priorities

- Import tolerance and dedupe.
- Analytics and metric confidence.
- Recommendation lifecycle and evaluation.
- AI payload/result persistence.
- Steam cursor handling and job status without real external jobs.

