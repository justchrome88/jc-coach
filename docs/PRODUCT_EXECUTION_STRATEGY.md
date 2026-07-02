# HISTORICAL / STRATEGY MEMO

This document is retained for context. Current product strategy and priority order are governed by `docs/PROJECT_CONTROL.md`, `docs/CURRENT_MILESTONE.md` and `docs/ROADMAP.md`.

# Product Execution Strategy

## Главный вектор

Мы строим не просто Scope.gg-клон. Главный продукт - AI CS2 Coach.

Scope-like статистика нужна как evidence layer:

```text
demo -> parser facts -> analytics -> mistakes -> recommendations -> progress tracking -> AI coach
```

## Что делать раньше расширенной красоты

1. Надежный DEM import.
2. Parser confidence и evidence.
3. Structured mistake detection.
4. AI coach handoff/result persistence.
5. Recommendation tracking по нескольким категориям.
6. Match detail как evidence экран.
7. Steam/FACEIT auth and auto import.
8. Расширенная аналитика.
9. UI polish.
10. 2D viewer в самый конец.

## Категории тренерского анализа

| Категория | Что оцениваем сейчас | Что понадобится позже | Статус |
|---|---|---|---|
| Aim | ADR, K/D, HS%, entry duel result | weapon breakdown, timing, accuracy | Partial |
| Map | winrate, ADR, entry diff по карте | позиции, callouts, side plans | Partial |
| Crosshair placement | пока нет надежных данных | координаты, view angles, death/kill positions | Planned |
| Grenades | utility damage, flash assists, enemies flashed best-effort | lineups, duration, enemy-only flash, outcome impact | Partial |
| Entry duels | entry kills/deaths | first contact timing, trade context | Partial |
| Survival | early deaths fallback, KAST | true early-death timing, trade/survive logic | Partial |
| Economy | пока нет | equipment/money/buy classification | Planned |

## Auth and auto import reality

Steam login should use Steam OpenID. Steam docs say a website can use OpenID to obtain a user's SteamID, without asking for Steam username/password.

Auto-import path should be staged:

1. Steam profile/linking scaffold.
2. Manual share code input.
3. Match auth code/share-code history import.
4. Demo download jobs.
5. Background sync.
6. Fresh-after-match polling.

FACEIT Data API is available, but FACEIT Downloads API requires separate access/application. So FACEIT full demo automation is not the first dependency unless access is granted.

## Commit discipline

Every block should end with:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
git status --short
git add ...
git commit -m "<small logical message>"
git push origin main
```

Do not keep huge uncommitted work. If a change is risky, split it.

## What to avoid now

- Clip recording.
- 2D viewer.
- Public social profiles.
- Rank benchmark datasets we do not own.
- Huge grenade library before parser evidence works.
- Crosshair placement claims before we have reliable view/position data.
