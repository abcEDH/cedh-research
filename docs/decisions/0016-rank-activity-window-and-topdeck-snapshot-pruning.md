# 0016 - Rank Activity Window and TopDeck Snapshot Pruning

## Status
Accepted

## Context
PR #263 fixed a bug where zero-game players (seeded with the `DEFAULT_RATING` anchor) could outrank real, games-backed players on the public leaderboard. Investigating the specific reported case (a player, Max Sternburg, shown at `topdeck_elo_rank = 1` on the homepage) surfaced two further, distinct root causes not covered by that fix:

1. **Stale TopDeck snapshot rows.** `packages/backend/src/import_topdeck_player_elos.py` upserted the fetched TopDeck Elo snapshot (`INSERT ... ON CONFLICT DO UPDATE`) but never deleted rows for players who dropped off TopDeck's published leaderboard (e.g. banned cheaters). A stale row (elo 2070, ranking 1, fetched 2026-05-06) survived the 2026-07-07 import and produced `topdeck_elo_rank = 1` for a player who had not played a rated game in months, because the homepage's "Global Leaderboard" surface sorts by `topdeck_elo_rank`. The 4 orphaned rows were deleted manually from production; the importer itself did not prevent recurrence.
2. **No activity rule.** The intended business rule — "players with no tournaments in the last 6 months are excluded from the rankings" — existed nowhere in the codebase. The affected player's last recorded game was 2025-09-20 (well over 6 months before the 2026-07-07 report), so this rule alone would have excluded them from rank 3 even with a fully accurate `topdeck_elo`.

## Decision
- **6-month (183-day) activity window for rank eligibility.** `packages/backend/src/regional_elo.py` defines `RANK_ACTIVITY_WINDOW_DAYS = 183`. A leaderboard row is rank-eligible (for both the games-backed `rank` field and `topdeck_elo_rank`) only if `games_played > 0` **and** `last_game_date` falls within `RANK_ACTIVITY_WINDOW_DAYS` of a reference date (defaults to today, UTC; injectable for tests). `last_game_date` is parsed defensively — it may arrive as a `date`, a `datetime`, an ISO string, or `None` — and a missing/unparseable value is treated as ineligible rather than defaulting to "active."
- **Ineligible rows receive `rank = None`, not a fallback ordinal.** An earlier revision of this fix sorted ineligible rows after all eligible ones but still assigned them a real, non-null `rank` (just a higher number). A Codex review pass on PR #263 caught that several `apps/web` read paths fall back to `rank` whenever `topdeck_elo_rank` is null (the player's own profile page, and the homepage's leaderboard preview), so that non-null fallback let an inactive/zero-game player show up with what looked like a real rank again — defeating the point of this activity gate. `global_elo_active_leaderboard.rank` is now nullable (migration `20260714120000_nullable_active_leaderboard_rank.sql`, mirroring the existing nullable `topdeck_elo_rank` column), ineligible rows get `rank = None`, and the homepage query (`apps/web/src/app/page.tsx`) now filters `rank IS NOT NULL` outright rather than risking `row.rank ?? index + 1` turning a null into a fabricated-looking list position.
- **TopDeck Elo imports are replace-snapshot, and prune the denormalized leaderboard too.** `import_topdeck_player_elos.py`'s `upsert_elo_rows()` deletes, in the same transaction as the upsert, any `topdeck_player_elos` row whose `topdeck_id` is not present in the freshly fetched snapshot, and logs the pruned count. As a safety guard, an empty fetched snapshot aborts the whole operation (upsert and delete) rather than wiping the table — an empty payload is far more likely to indicate a transient fetch/parse failure than a genuine full delisting. A second Codex finding on PR #263 pointed out that the daily prune only touched the raw `topdeck_player_elos` snapshot — the public leaderboard actually reads the separately-rebuilt, denormalized `global_elo_active_leaderboard` table, so a delisted player's already-materialized `topdeck_elo`/`topdeck_elo_rank` kept showing there until a full leaderboard rebuild happened to run. `upsert_elo_rows()` now also nulls those two columns directly, in the same transaction, for every pruned `topdeck_id`. This doesn't re-tighten the rank *numbers* of other players in the same partition (that still needs a full rebuild) but it does immediately clear the stale/phantom rank itself.
- **TopDeck Elo is the primary ranking on the homepage, refreshed daily.** `.github/workflows/topdeck-elo-import.yml`'s schedule moved from weekly (`0 16 * * 2`, Tuesdays) to daily (`0 16 * * *`), so delisted players are pruned and rank changes propagate within a day instead of up to a week. Our own internally-computed `rank`/`rating` is kept as a secondary, lower-visibility signal (used as a fallback only for eligible players who lack a TopDeck import), not surfaced as the primary/authoritative ranking.

## Consequences

**Easier**
- Delisted TopDeck players (cheaters, account actions) disappear from `topdeck_player_elos` automatically on the next import instead of requiring a manual cleanup query.
- The "6 months inactive" rule is now a single named constant and testable predicate instead of an unwritten expectation.
- Daily refresh means the leaderboard reflects TopDeck-side changes (delistings, rating updates) within ~24h.

**Harder**
- A player who is legitimately inactive for slightly over 6 months disappears from ranked views even if their historical rating/topdeck_elo would still be competitive; there is no grace period or manual override.
- The importer now performs a delete every run; a bug in the fetch step that silently returns a partial (but non-empty) snapshot could prune players who are still on TopDeck's real leaderboard. The empty-snapshot guard only protects against the fully-empty case.
- Daily runs increase TopDeck API call volume roughly 7x versus the weekly schedule.

### Cross-Repo Impact
Primarily `packages/backend/` (`regional_elo.py`, `import_topdeck_player_elos.py`, a new migration making `global_elo_active_leaderboard.rank` nullable, `.github/workflows/topdeck-elo-import.yml`). One `apps/web/` change: `apps/web/src/app/page.tsx`'s homepage leaderboard preview query now filters `rank IS NOT NULL`, since `rank` can be null now and the previous assumption that the web app could treat it as an opaque, always-present field no longer held once ineligible rows stopped getting a fallback ordinal.

## Sources
- PR #263 — "Fix leaderboard rank-1 bug: zero-game players outranking rated players" (base fix + this follow-up)
- Issue #252
- `packages/backend/src/regional_elo.py` — `RANK_ACTIVITY_WINDOW_DAYS`, `_is_rank_eligible`, `_is_topdeck_rank_eligible`, `build_active_leaderboard_rows`
- `packages/backend/src/import_topdeck_player_elos.py` — `upsert_elo_rows`
- `.github/workflows/topdeck-elo-import.yml`
