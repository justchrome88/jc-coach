# PROMPT-PLAYBOOK-03 Language Policy Report

## Result

PASS. Added the prompt language policy clarification to the prompt playbook and confirmed the handoff pointer.

## Changed files

- `docs/project_management/PROMPT_PLAYBOOK.md`
- `docs/HANDOFF.md`
- `docs/refactor/PROMPT-PLAYBOOK-03_LANGUAGE_POLICY_REPORT.md`

## Policy added

- Direct ChatGPT-to-user explanations stay Russian by default.
- Codex task prompts may be written in English.
- Codex console output and internal reports may be English.
- Short user-facing notes may be Russian when helpful.
- Human-facing product docs should be Russian when meant for direct user reading.
- Long internal technical reports/docs may be English if that reduces token cost and keeps meaning clear.
- Language choice does not change scope, safety rules, source-of-truth order, or authorization requirements.

## Checks

- `git diff --check`: PASS
- `git status --short`: expected docs-only changes in the allowed paths.

## Warnings

- None.

## Recommended next task

Use the language policy in future ChatGPT-generated Codex task prompts without changing task scope or safety gates.
