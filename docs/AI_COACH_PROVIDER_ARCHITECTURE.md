# AI Coach Provider Architecture

## Решение

Не привязываем продукт к OpenAI API. На текущем этапе используем `codex_cli_handoff`: приложение готовит structured payload и prompt, а Codex CLI выступает мозгом в human-in-the-loop режиме.

Позже подключаем `local_llm` provider через тот же интерфейс.

## Почему так

- У владельца проекта сейчас нет OpenAI API key.
- Главный вектор продукта - AI-тренер, но AI должен работать поверх проверенных CS2-фактов.
- Ранний этап требует гибкости: сначала можно разбирать отчёты через Codex CLI, потом заменить backend модели.
- Локальная LLM вероятна как целевой вариант, поэтому provider boundary нужен сразу.

## Поток данных

```text
DEM / CSV / JSON
  -> deterministic parser and analytics
  -> structured coach payload
  -> AIProvider
      -> codex_cli_handoff now
      -> local_llm later
  -> AI coach report
```

## Текущий provider: codex_cli_handoff

Кнопка `/coach -> Подготовить AI handoff` создает папку в:

```text
data/ai_handoffs/YYYYMMDDHHMMSS/
```

Файлы:

| Файл | Назначение |
|---|---|
| `coach_payload.json` | Машиночитаемые факты: summary, trends, weaknesses, recommendation progress, recent matches |
| `codex_prompt.md` | Готовый prompt для Codex CLI |
| `metadata.json` | Provider, статус, пути и команда запуска |

## Future provider: local_llm

Планируемый env:

```text
AI_PROVIDER=local_llm
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=your-model
```

Целевые варианты:

- Ollama;
- LM Studio;
- любой OpenAI-compatible local server.

## Правила AI coach

- AI не парсит demo.
- AI не выдумывает факты.
- AI получает только structured payload.
- Если данных мало, AI обязан сказать о низком confidence.
- Основной output: диагноз, 3 главные ошибки, план на неделю, метрики контроля.

## Следующий шаг

1. Сохранять результат AI-разбора обратно в `coach_reports` или отдельную таблицу `ai_coach_reports`.
2. Добавить ручную вставку результата из Codex CLI в UI.
3. После стабилизации structured mistakes подключить `local_llm`.
