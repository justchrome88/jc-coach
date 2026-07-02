# Steam Import

Last updated: 2026-07-03.

Canonical supporting docs:

- `docs/STEAM_IMPORT_ARCHITECTURE.md`
- `docs/STEAM_MATCH_DATES_RU.md`

## Accepted Flow

1. User signs in with Steam OpenID.
2. User provides Game Authentication Code and latest `CSGO-...` share-code cursor from Steam Support.
3. Server operator configures `STEAM_WEB_API_KEY`.
4. Dedicated service bot resolves known share codes through the CS2 Game Coordinator.
5. App downloads `.dem.bz2`, decompresses to `.dem`, imports through parser and stores Steam GC `match_time` as authoritative `played_at`.

## Current Status

Steam import is an alpha path, not production-ready.

## Known Risks

- Service bot cannot enumerate private user history by itself.
- `knowncode=0` is not a valid substitute for a latest cursor and can fail.
- Stale cursor can point behind already imported history.
- Valve replay URLs can expire or return transient 502/404/410.
- Durable retry/backoff and scheduler behavior still need hardening.

## Product Rule

Do not turn Steam import into manual share-code entry for every match. The target UX is one-time onboarding plus background sync with clear cursor freshness diagnostics.

