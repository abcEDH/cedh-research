# Changes Summary (2026-04-09)

## Backend / Backfill

- Updated `packages/backend/src/backfill_moxfield_commanders.py` so the backfill can:
  - process a Supabase-derived target list via `--entry-ids-file`
  - operate over all targeted Moxfield rows instead of only unknown commanders
  - rewrite `decklist_url` to a TopDeck deck page when available
  - update `commander_id` only when the current commander is missing or placeholder
  - enforce the passed date window locally instead of trusting the unstable relation filter
- Added a temporary dedicated URL rewrite script during iteration, then consolidated the real workflow back into the commander backfill.
- Generated the in-range target manifest at `logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt`.
- Documented the post-run retry plan for transient failures in [backfill-followups.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/backfill-followups.md).

## Current Backfill Status

- Active job:
  - `packages/backend/src/backfill_moxfield_commanders.py`
  - PID `46196`
  - target file: `logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt`
  - attempt cache: `logs/backfill_moxfield_commanders_targeted_run_20260408.csv`
- Latest checked status:
  - target rows: `55,361`
  - attempted: `30,413`
  - remaining: `24,948`
  - completed: `54.9%`
- Breakdown at last check:
  - `resolved`: `21,496`
  - `no_commander_found`: `3,899`
  - `moxfield_redirect`: `3,090`
  - `bad_moxfield_url`: `1,874`
  - `topdeck_connection_error`: `27`
  - `topdeck_timeout`: `14`
  - `topdeck_http_error`: `4`
  - `supabase_update_failed`: `9`
- Recent pace at last check:
  - `828` rows / 10 minutes
  - about `4,968` rows / hour

## Frontend Leaderboard

- Renamed the leaderboard filter label from `View` to `Country`.
- Renamed the player-page back link from `region-filtered leaderboard` to `region leaderboard`.
- Changed the leaderboard columns so:
  - `Latest` became `Latest Tournament`
  - `Latest Tournament` shows the tournament name and links to TopDeck
  - `Active Commander` is a dedicated column placed between `Elo` and `Games`
  - `Active Commander` links to the most recent decklist for that commander when available
- Updated leaderboard data assembly so:
  - active commander uses the same source-of-truth logic as the profile page
  - latest tournament is chosen from the latest playable tournament context instead of unstable query ordering
- Updated country leaderboard behavior so country-wide `ALL states` views only include players whose inferred home country matches the selected country.
- Fixed the legacy country-view fallback so it no longer silently falls back to the global leaderboard and no longer shows players like Alexander Bye in the wrong country view.
- Removed the temporary human-name selection heuristic after confirming the current schema does not store historical per-event player names.

## Frontend Player Profile

- Added `Record Against Opponents`.
- Added `Record Against Commanders`, based on the commanders opponents were playing.
- Deduped commander matchup counting per game so duplicate same-commander seats in one pod only count once for that commander.
- Normalized empty commander labels and `Unknown Commander` to `Unknown`, and pinned `Unknown` to the bottom of the commander records table.
- Added `Best Matchup` and `Worst Matchup` summaries for both opponents and commanders, and moved those summaries into the top of the corresponding record cards.
- Added a `Country Rank` card and aligned it with the same country-membership logic used by the leaderboard.
- Reworked the profile summary cards so:
  - `Country Rank` shows the rank prominently with country as secondary text
  - `State Rank` shows the rank prominently with state as secondary text
  - `TopDeck` was renamed to `TopDeck Rank`
- Removed extra profile-page copy including:
  - `TopDeck Player Profile`
  - the old global/state-slice explainer under the player name
  - the old TopDeck/home-region explainer under the stat cards

## Matchup Algorithm

- Added documentation in [player-matchup-algorithm.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/player-matchup-algorithm.md).
- Current algorithm:
  - draw weight: `0.2`
  - prior games: `20`
  - adjusted score uses Bayesian-style shrinkage toward the player baseline
  - no minimum-games gate for selecting a best/worst matchup
- Updated the UI to show a best guess whenever matchup data exists, instead of suppressing results for small samples.

## Player Profile Data Fixes

- Fixed truncation in opponent matchup aggregation caused by fetching too many opponent rows in a single capped page.
- Paginated the remaining player-profile fetch paths that had the same class of bug:
  - event log fetches
  - commander usage fetches
  - raw tournament entry fetches
- Verified the Anthony GlacialCity / Albert Burse opponent counts are now symmetric at `11` games on both profile pages.

## PR / CI Follow-ups

- Fixed follow-up CI issues on PR 48 by:
  - importing `Any` where needed in the backend
  - adding `server-only` as a real frontend dependency
  - mocking `server-only` in shared Vitest setup
  - making the `Retry-After` test deterministic
  - fixing `regional-elo/page.tsx` search-param typing/build issues
- Updated [pr-48-summary.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/pr-48-summary.md) to reflect those fixes.
