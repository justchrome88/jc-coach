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

Stage 1 security hardening verifies Steam OpenID callback assertions through Steam `check_authentication` before linking an account. A callback that only provides a `claimed_id` is rejected.

Stage 2 ownership hardening requires current owner session for `/auth/steam/callback`. Без owner session callback не создаёт uncontrolled user, `steam_accounts` или `import_jobs`. При owner session Steam account линкуется только к owner user.

## Known Risks

- Service bot cannot enumerate private user history by itself.
- `knowncode=0` is not a valid substitute for a latest cursor and can fail.
- Stale cursor can point behind already imported history.
- Valve replay URLs can expire or return transient 502/404/410.
- Durable retry/backoff and scheduler behavior still need hardening.
- Steam OpenID network verification can fail closed if Steam is unreachable.
- Low-level helper `link_steam_account(..., user_id=None)` still supports legacy Steam-only user creation for old service paths; public OpenID callback no longer uses this path without owner.

## Product Rule

Do not turn Steam import into manual share-code entry for every match. The target UX is one-time onboarding plus background sync with clear cursor freshness diagnostics.
