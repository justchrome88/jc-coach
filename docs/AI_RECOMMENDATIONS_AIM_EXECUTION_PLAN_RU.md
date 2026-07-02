# План доведения AI persistence, multi-category recommendations и aim stats

Дата старта: 2026-07-01.

## Принцип реализации

- Делать проще, но без потери проверяемости.
- Не выдумывать метрики, которых нет в parser payload.
- Улучшать связанные фичи комплексно, чтобы не плодить параллельные сущности.
- Каждый этап должен иметь тесты, документацию и запись в `WORKLOG.md`.

## Связанные пункты roadmap

### AI coach result persistence

Родственные пункты:

- `AI coach report`
- `AI provider abstraction`
- `AI coach handoff`
- `Coach report`
- `Mistake detection`

Что полезно сейчас:

- Хранить не только markdown ответа, но и snapshot входного payload.
- Хранить provider/status/payload hash в `coach_reports.report_json`.
- Дать API истории AI reports, а не только latest.
- В UI показывать источник, provider, payload hash и список последних AI reports.

Что не делать сейчас:

- Не делать сложную систему eval/feedback до появления реальных AI reports.
- Не требовать OpenAI/local model для базового persistence.

План:

1. Расширить сохранение AI result metadata без миграции схемы: использовать `report_json`.
2. Добавить `list_ai_coach_reports()` и сериализацию report metadata.
3. Добавить API history endpoint.
4. Обновить `/coach` UI.
5. Добавить тесты на metadata/snapshot/history.

## Multi-category recommendations

Родственные пункты:

- `Active training goal`
- `Per-match goal status`
- `Recommendation lifecycle`
- `Progress tracking`
- `Multi-category recommendations`
- `Mistake detection`
- `Training routines`

Что полезно сейчас:

- Не просто pause/done/archive, а restart/extend по категории.
- История целей по категориям: active/paused/completed/archived.
- Явный category summary для AI payload и API.
- Сохранять текущий baseline при restart, чтобы новый цикл начинался после текущих матчей.

Что не делать сейчас:

- Не делать произвольный конструктор целей до стабилизации правил.
- Не делать сложный UI создания custom goals, пока нет пользовательских сценариев.

План:

1. Добавить restart системной рекомендации по category.
2. Добавить extend target period.
3. Добавить `list_recommendation_history()` и category summary.
4. Добавить API/UI actions.
5. Добавить тесты на restart/extend/history.

## Aim stats

Родственные пункты:

- `Aim stats`
- `First duels`
- `ADR`
- `Crosshair placement coach`
- `Mistake detection`
- `AI coach report`

Что полезно сейчас:

- Считать честные aim metrics из доступных данных:
  - ADR;
  - K/D;
  - HS%;
  - damage per death;
  - opening duel success;
  - multi-kill rounds;
  - weapon breakdown из `player_death`/`player_hurt`, если demo parser дал weapon fields.
- Показывать data gaps для accuracy, first bullet, spray, TTK и crosshair placement.
- Добавить aim profile в `/stats`, `/coach`, match detail и AI payload.

Что не делать сейчас:

- Не заявлять accuracy/spray/TTK/crosshair placement без надежных shots/view-angle/position данных.
- Не строить отдельный сложный aim dashboard до появления нескольких надежных demo samples.

План:

1. Расширить parser payload: `aim_summary`, `weapon_breakdown`, `aim_data_gaps`.
2. Добавить `app/services/aim_stats.py` для aggregate profile по матчам.
3. Добавить aim profile в AI payload и UI.
4. Добавить API endpoint для aim stats.
5. Добавить тесты parser/service/API smoke.

## Журнал выполнения

- 2026-07-01: создан план, выявлены связанные roadmap пункты.
- 2026-07-01: AI coach result persistence доведен:
  - сохраняется snapshot payload;
  - пишется provider/status/payload hash/content metadata в `coach_reports.report_json`;
  - добавлен список последних AI reports в `/coach`;
  - добавлен `GET /api/coach/ai/results`;
  - тесты покрывают metadata и history.
- 2026-07-01: multi-category recommendations доведены:
  - добавлены extend/restart/status actions;
  - добавлена история и сводка категорий;
  - добавлены API endpoints history/categories/extend/restart;
  - UI `/coach` показывает lifecycle summary и history;
  - тесты покрывают extend/restart/history/category summary.
- 2026-07-01: aim stats доведены до честного MVP:
  - parser сохраняет `aim_summary`, `weapon_breakdown`, `aim_data_gaps`;
  - добавлен `app/services/aim_stats.py`;
  - добавлен `GET /api/analytics/aim`;
  - aim profile подключен в `/stats`, `/coach`, match detail и AI payload;
  - tests покрывают parser payload и aggregate aim profile.
- 2026-07-01: исправлен runtime rollout:
  - после изменения templates/context сервис был перезапущен;
  - live-smoke с authenticated session показал 200 для `/dashboard`, `/stats`, `/coach`, `/matches`, `/settings/imports`, `/settings/storage`, `/upload`, `/report`;
  - правило restart + authenticated live-smoke добавлено в `instructions/03_CODEX_AGENT_RULES.md`.

## Что нужно от пользователя

Пока ничего не блокирует работу.

Перед включением удаления raw `.dem` нужно утвердить обязательный набор raw/aim метрик:

- какие round-level события сохранять;
- нужен ли per-weapon damage/headshot/death breakdown как обязательный;
- нужны ли позиции/tick timeline для будущего crosshair/positioning анализа;
- какие метрики считаются достаточными для статуса `parsed_payload_verified`.
