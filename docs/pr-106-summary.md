# PR 106 Summary

## Summary

This PR fixes TopDeck tournaments whose completed games were stored in TopDeck's flat Firestore bracket fields but were not represented in Supabase. The issue mainly affected league-style events, but the full scan also found non-league events using the same flat pod format.

- Adds ingest support for flat Firestore pod rounds when the TopDeck API payload does not expose all completed games.
- Adds a one-time backfill utility that scans every stored TopDeck tournament for missing flat pod games.
- Backfills all affected Supabase game and participant rows.
- Rebuilds Global Elo derived tables after the corrected game stream is written.

## Backend Ingest

- Updated [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py) so tournament fetches can augment normal TopDeck API payloads with flat Firestore pod rounds.
- Added a merge path that preserves existing API rounds while prepending missing flat numeric rounds.
- Added a flat-only Firestore fetch path for tournaments that already have API rounds, avoiding broader legacy Firestore fallback behavior when only flat pod augmentation is needed.
- Verified future ingest behavior against:
  - `Vj6FWrItL4z50jpYo7tH`, which resolves `529` numeric flat tables.
  - `8QZK2QqFnRwEhfPYs0Nc`, which resolves `1,350` numeric flat tables.

## Historical Backfill

- Added [backfill_flat_firestore_games.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_flat_firestore_games.py) to scan and repair missing flat Firestore pod games.
- The script:
  - scans all Supabase tournaments with a `topdeck_tid`
  - fetches the matching TopDeck Firestore tournament document
  - extracts completed, unmuted flat `S<round>:T<table>` pod rows
  - compares flat completed pod counts against stored numeric game rows
  - upserts missing `games` rows by `game_key`
  - upserts `game_participants` rows by `game_id,entry_id`
  - creates missing tournament entries when flat pod players were not present in existing standings-derived entries
  - uses `Unknown Commander` for missing entry commander metadata when Firestore exposes only player IDs
- The full scan covered `13,020` tournaments.
- Found `22` tournaments with missing flat pod games.
- Initial missing numeric-game delta was `17,308`.
- Total completed flat pod games across affected tournaments was `17,678`.
- Backfilled/upserted:
  - `17,678` flat pod games
  - `70,707` participant rows
- Re-ran the full scan after backfill and found `0` tournaments still missing flat pod games.

## Global Elo Rebuild

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
- Current table counts after the rebuild:
  - `games`: `268,157`
  - `game_participants`: `994,649`
  - `tournaments`: `13,020`

## Validation

- Post-backfill full scan reported `Found 0 tournaments with missing flat pod games`.
- Spot checks:
  - CriticalEDH August 2025 League has `1,350` numeric flat-pod games.
  - CriticalEDH November 2025 League has `2,692` numeric flat-pod games.
  - CriticalEDH October 2025 League has `3,052` numeric flat-pod games.
  - The previously reported August player row now verifies at `17` games with record `8-7-2`.
- Python compile check passed:
  - `python3 -m py_compile packages/backend/src/ingest.py packages/backend/src/backfill_flat_firestore_games.py packages/backend/src/rebuild_global_elo_tables.py`

## Notes

- The flat Firestore tournament format often exposes player IDs but not player names or decklists. For missing tournament entries created during backfill, the script preserves existing known player rows when available and only creates absent players as `Unknown`.
- `.idea/workspace.xml` was already modified in the local worktree and is unrelated to this PR.
