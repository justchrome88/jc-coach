# Правила для Codex-агентов

Канонические инструкции для Codex и других AI-агентов в этом репозитории.

## Обязательное чтение перед любой задачей

Перед любыми изменениями или проверками агент обязан:

1. Прочитать `AGENT.md`.
2. Прочитать `docs/PROJECT_CONTROL.md`.
3. Прочитать `docs/PROJECT_OS.md`.
4. Прочитать `docs/HANDOFF.md`.
5. Прочитать `docs/CURRENT_MILESTONE.md`.
6. Выполнить `git status --short`.
7. Запустить `python scripts/project_gate.py preflight`, если задача не запрещает shell-проверки.
8. Запустить `python scripts/project_gate.py changed` и прочитать активированные `docs/agents/*`, если есть изменённые пути.
9. Прочитать релевантный доменный документ из `docs/`, если задача касается конкретной области.

Если старый README, roadmap, prompt, audit или `instructions/*` конфликтует с `docs/PROJECT_CONTROL.md`, следовать `docs/PROJECT_CONTROL.md`.

## Жёсткие границы

- Задачи вне текущего milestone запрещены без явного разрешения пользователя.
- Не менять код приложения, если задача прямо этого не разрешает.
- Не менять модели БД, миграции, runtime data или live data, если задача прямо этого не разрешает.
- Не запускать imports, Steam jobs, parser jobs, background imports или bulk jobs, если задача прямо этого не разрешает.
- Не удалять старые документы без deprecation plan в `docs/audit/DOCUMENT_DEPRECATION_PLAN.md`.
- Не делать `git commit`, `git push` или deploy, если пользователь явно не попросил.
- Не коммитить `.env`, DB files, raw demos, generated reports, handoff files, bot credentials, refresh tokens или `node_modules`.
- Не перезапускать `jc-coach.service`, если задача прямо не требует runtime repair/deploy smoke и пользователь это не разрешил.

## Направление продукта

Это персональный CS2 coach. Продукт должен идти по циклу:

```text
Match -> Facts -> Metrics -> Diagnosis -> Primary Recommendation -> Evaluation -> Progress -> AI Explanation
```

Текущий milestone описан в `docs/CURRENT_MILESTONE.md`. Новые фичи запрещены до закрытия hardening-задач текущего milestone, если пользователь явно не изменил приоритет.

## После работы

- Показать изменённые файлы.
- Запустить `python scripts/project_gate.py postflight`, если задача выполнялась в shell.
- Обновить релевантные docs, если изменилось поведение, процесс, архитектура, статус проекта или source-of-truth.
- Запускать только безопасные тесты и проверки.
- Если тесты пропущены из-за риска production DB/runtime data, явно написать почему.
- Не делать commit, если пользователь явно не попросил.

## Правила документации

- Обновлять `docs/PROJECT_CONTROL.md`, если изменилась текущая правда, приоритеты, ограничения или source-of-truth map.
- Держать `README.md` коротким входом для пользователя/оператора, а не стратегическим документом.
- Считать `WORKLOG.md` хронологией, а не текущим контрактом состояния.
- Помечать устаревшие docs как historical/deprecated перед переносом или удалением.
- Сохранять исторический контекст, пока он намеренно не перенесён и не одобрен к удалению.
