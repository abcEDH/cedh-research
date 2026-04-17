# PR 106 Summary

## Summary

This PR fixes missing TopDeck flat Firestore pod games and updates player profiles to make tournament finishes easier to inspect. The backend changes make future ingests include completed flat pod rounds, while the backfill script repairs historical Supabase rows. The frontend changes add a paginated, searchable Achievements section to player profiles and make profile totals use the game-log source of truth.

Changed files in PR 106:

- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx)
- [pr-106-summary.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/pr-106-summary.md)
- [backfill_flat_firestore_games.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_flat_firestore_games.py)
- [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py)

## Player Profiles

- Adds an Achievements section to player profile pages.
- Places Achievements at the bottom of the profile page.
- Fetches tournament finishes from `tournament_entries`, including:
  - tournament name
  - TopDeck tournament ID
  - start date
  - player count
  - final standing
  - commander
  - decklist URL
  - stored entry record fields
- Sorts achievements by finish quality:
  - lower `placement / player_count` first
  - larger player count as the first tie-breaker
  - more recent tournament as the second tie-breaker
- Recomputes each achievement's W-L-D from the player's actual game logs for that tournament/date, so league entries no longer show stale `0-0-0` records when game rows exist.
- Filters Achievements to rows where the player has at least one recorded game.
- Shows 10 achievement rows per page.
- Adds Achievements pagination with Previous/Next links and a page counter.
- Preserves the selected region, tournament search, commander search, and page number in achievement pagination links.
- Adds tournament-name search inside Achievements.
- Adds commander-name search inside Achievements.
- Adds a Clear link for achievement searches.
- Links tournament names to the TopDeck bracket when `topdeck_tid` is available.
- Links the commander name to the tournament decklist when a decklist URL exists, falling back to the TopDeck deck page URL for that tournament/player.
- Removes the share column from the achievement table.
- Keeps the Achievements section label as `Tournament finishes`.
- Updates top-level Games/Record profile cards to use totals from the current player game logs, matching the Overall row in Seat Distribution instead of falling back to potentially stale summary rows.
- Updates the Played Commanders helper text to say: `Commanders from all stored games for this player, sorted by last played.`

## Backend Ingest

- Updates [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py) so TopDeck tournament fetches can include completed flat Firestore pod rounds.
- Adds `merge_firestore_flat_league_rounds()` to merge flat Firestore rounds into a TopDeck-like tournament payload without duplicating existing round keys.
- Preserves existing API rounds and prepends missing flat numeric rounds.
- Updates `swissNum` when flat rounds contain a higher numeric round count.
- Tracks merged source metadata for debugging.
- Updates the legacy Firestore fallback path so legacy structured rounds and flat pod rounds can be merged instead of choosing only one source.
- Adds `get_firestore_flat_tournament()` for tournaments that already have API rounds, so ingest can augment only the flat pod rows without replacing the full API payload with the broader legacy Firestore fallback.
- Handles Firestore `404` as no flat payload and logs non-404 Firestore fetch failures without failing the whole API tournament fetch.
- Verified future ingest behavior against:
  - `Vj6FWrItL4z50jpYo7tH`, which resolves `529` numeric flat tables.
  - `8QZK2QqFnRwEhfPYs0Nc`, which resolves `1,350` numeric flat tables.

## Flat Pod Backfill

- Adds [backfill_flat_firestore_games.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_flat_firestore_games.py) to scan and repair missing TopDeck flat Firestore pod games.
- The script can:
  - scan all Supabase tournaments with `topdeck_tid`
  - optionally limit the scan to league-named tournaments with `--only-leagues`
  - write issue manifests with `--issues-out`
  - replay an issue manifest with `--issues-in`
  - limit issue processing with `--limit`
  - control Firestore scan concurrency with `--workers`
  - dry-run by default and write only with `--apply`
- The scanner:
  - fetches each TopDeck Firestore tournament document
  - extracts completed, unmuted flat `S<round>:T<table>` pod rows
  - ignores muted pods, unfinished pods, pods without winners, and pods with fewer than two resolved players
  - treats `_DRAW_` winners as draw games
  - compares completed flat pod counts against stored numeric Supabase game rows
- The writer:
  - upserts `games` by `game_key`
  - upserts `game_participants` by `game_id,entry_id`
  - writes `result` as `win`, `loss`, or `draw`
  - writes `points_earned` as `5` for wins, `1` for draws, and `0` for losses
  - creates missing tournament entries when flat pod players were not present in existing standings-derived entries
  - preserves existing known player rows when possible
  - creates absent player rows as `Unknown` only when Firestore exposes only the TopDeck player ID
  - uses `Unknown Commander` for missing entry commander metadata
  - chunks game, participant, and entry writes for large events
  - is idempotent, so interrupted runs can be retried safely

## Supabase Repair

- Scanned `13,020` stored TopDeck tournaments.
- Found `22` tournaments with missing flat pod games.
- Initial missing numeric-game delta was `17,308`.
- Total completed flat pod games across affected tournaments was `17,678`.
- Backfilled/upserted:
  - `17,678` flat pod games
  - `70,707` participant rows
- Re-ran the full scan after backfill and found `0` tournaments still missing flat pod games.
- Current table counts after repair:
  - `games`: `268,157`
  - `game_participants`: `994,649`
  - `tournaments`: `13,020`

## Global Elo Refresh

- Rebuilt derived Global Elo tables after the game and participant rows were corrected.
- Rebuild input:
  - `994,649` participant result rows
  - `257,063` games
- Rebuilt output:
  - `84,149` ratings
  - `52,029` state activity rows
  - `992,250` game events
  - `69,460` active leaderboard rows
  - `84,149` player profile summaries

## Validation

- Confirmed the GitHub PR file list for PR 106 contains four files:
  - player profile page
  - PR summary doc
  - flat Firestore backfill script
  - ingest flat-round merge support
- Post-backfill full scan reported `Found 0 tournaments with missing flat pod games`.
- Spot checks:
  - CriticalEDH August 2025 League has `1,350` numeric flat-pod games.
  - CriticalEDH November 2025 League has `2,692` numeric flat-pod games.
  - CriticalEDH October 2025 League has `3,052` numeric flat-pod games.
  - The previously reported August player row verifies at `17` games with record `8-7-2`.
- Python compile check passed:
  - `python3 -m py_compile packages/backend/src/ingest.py packages/backend/src/backfill_flat_firestore_games.py packages/backend/src/rebuild_global_elo_tables.py`

## Notes

- The flat Firestore tournament format often exposes player IDs but not player names or decklists. Missing tournament entries created during backfill therefore use existing known player data when available and only fall back to `Unknown` when no local player row exists.
- `.idea/workspace.xml` is modified in the local worktree but is not part of PR 106.
