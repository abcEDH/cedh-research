# PR 81 Summary

## Summary

This PR tightens the regional Elo leaderboard/profile experience, expands player matchup drilldowns, and adds follow-up tooling for historical Moxfield commander cleanup and canonical leaderboard count fixes.

- Improves the regional/global leaderboard UI and player profile pages:
  - renames the leaderboard filter label from `View` to `Country`
  - adds a dedicated `Active Commander` column with latest decklist links when available
  - changes `Latest` to `Latest Tournament` and links it to TopDeck
  - fixes country filtering so country-wide views only include players assigned to that country
  - removes incorrect fallback behavior that could show global rows in country views
- Expands player profile drilldowns:
  - adds `Record Against Opponents`
  - adds `Record Against Commanders`
  - adds best/worst matchup summaries for both opponents and commanders
  - adds a `Country Rank` card and aligns rank logic with leaderboard country membership
  - updates `Seat Distribution` with an `Overall` row and score formula
  - removes extra explainer copy and simplifies the profile layout
- Fixes player-profile data correctness:
  - paginates matchup, event-log, commander-usage, and tournament-entry fetch paths that were truncating profile aggregates
  - dedupes same-commander seats within a pod for commander matchup counts
  - normalizes empty/unknown commander labels to `Unknown`
  - verifies previously asymmetric opponent counts are now consistent
- Adds documentation for the matchup scoring model in [player-matchup-algorithm.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/player-matchup-algorithm.md)
- Adds Moxfield/TopDeck cleanup tooling:
  - extends `packages/backend/src/backfill_moxfield_commanders.py` to support DB-derived target manifests, full-row processing, TopDeck deck-page rewrites, safer local date-window enforcement, and safer resume/retry behavior
  - adds [backfill_topdeck_decklist_urls.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_topdeck_decklist_urls.py) as a focused TopDeck URL rewrite utility
  - adds [sweep_partner_commander_order.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/sweep_partner_commander_order.py) to normalize partner ordering using observed usage plus explicit overrides
  - documents the backfill follow-up workflow in [backfill-followups.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/backfill-followups.md)
  - adds the partner review artifact in [partner-community-order-review.csv](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/partner-community-order-review.csv)
- Fixes leaderboard/profile canonical counts:
  - adds [20260409140000_fix_global_leaderboard_canonical_counts.sql](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/supabase/migrations/20260409140000_fix_global_leaderboard_canonical_counts.sql)
  - makes displayed games, wins, draws, losses, and last played derive from canonical `global_elo_game_events` aggregates instead of potentially stale rating counters
- Fixes PR follow-up issues:
  - resolves the frontend `next build` nullability failure in latest-tournament matching
  - switches backend maintenance CI from stale inline workflow checks to the maintained `ci_backend_checks.py` script
  - aligns backend maintenance validation with the currently deployed regional Elo schema and canonical state-activity consistency checks
  - updates the backend data dictionary for the canonical leaderboard-count migration
  - keeps docs checks resilient to deleted tracked markdown files in the working tree

## Backend / Backfill

- Updated `packages/backend/src/backfill_moxfield_commanders.py` so the backfill can:
  - process a Supabase-derived target list via `--entry-ids-file`
  - operate over all targeted Moxfield rows instead of only unknown commanders
  - rewrite `decklist_url` to a TopDeck deck page when available
  - update `commander_id` only when the current commander is missing or placeholder
  - enforce the passed date window locally instead of trusting the unstable relation filter
- Hardened the same script further so:
  - `--entry-ids-file` resume can skip already-attempted IDs instead of rescanning from index `0`
  - retry mode uses cached retry IDs directly instead of conflicting with the normal resume path
  - attempt-cache loading strips NUL bytes before CSV parsing
- Added [backfill_topdeck_decklist_urls.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_topdeck_decklist_urls.py) as a focused utility to rewrite stored Moxfield deck URLs to native TopDeck deck pages when those pages resolve cleanly.
- Added [sweep_partner_commander_order.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/sweep_partner_commander_order.py) as a one-time normalization sweep for partner commander ordering, using observed usage plus explicit community-order overrides and documenting the review set in [partner-community-order-review.csv](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/partner-community-order-review.csv).
- Generated the in-range target manifest at `logs/moxfield_entry_ids_2023-12-08_to_2025-10-05.txt`.
- Documented the post-run follow-up plan in [backfill-followups.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/backfill-followups.md), including:
  - a gap pass for target IDs missing from the attempt cache
  - a transient retry pass for `topdeck_timeout`, `topdeck_connection_error`, `supabase_update_failed`, and `topdeck_http_error`
  - a final reconciliation check to confirm all target IDs are logged
- Added [20260409140000_fix_global_leaderboard_canonical_counts.sql](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/supabase/migrations/20260409140000_fix_global_leaderboard_canonical_counts.sql) so leaderboard and profile global counts come from canonical `global_elo_game_events` aggregates instead of potentially stale rating-table counters.

## Current Backfill Status

- The original main targeted run is no longer the current source of truth for progress tracking.
- Follow-up work moved to DB-derived residual manifests so progress is measured against rows that still store a Moxfield `decklist_url` in the target date window.
- The second residual run was restarted with a seeded non-retry cache so previously accepted permanent outcomes were skipped instead of being reprocessed:
  - target file: `logs/moxfield_entry_ids_remaining_in_range_postrun.txt`
  - seeded attempt cache: `logs/backfill_moxfield_commanders_residual_in_range_postrun_seeded_nonretry_20260409_055003.csv`
  - seeded skip set: `43,360` rows
  - resumed work queue after seeded skips: `27,669` rows
- That seeded rerun has now completed.
- Final seeded rerun counters:
  - `scanned`: `19,105`
  - `updated`: `4,955`
  - `unresolved`: `6,033`
  - `bad_url_skipped`: `1,170`
  - `decklist_updated`: `16,153`
  - `topdeck_requests`: `17,935`
  - `moxfield_requests`: `0`
- Final seeded cache totals:
  - `resolved`: `42,844`
  - `no_commander_found`: `8,188`
  - `moxfield_redirect`: `6,225`
  - `bad_moxfield_url`: `5,179`
  - `topdeck_timeout`: `18`
  - `supabase_update_failed`: `7`
  - `topdeck_connection_error`: `4`
- Next step remains a fresh DB-side reconciliation to measure the real remaining residual set after this completed seeded pass.

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
  - latest tournament is now derived from each player's latest actual game event instead of the old tournament-entry proxy
  - tournament names and TopDeck bracket links are recovered from `tournaments` after selecting the latest played event
- Updated country leaderboard behavior so country-wide `ALL states` views only include players whose inferred home country matches the selected country.
- Fixed the legacy country-view fallback so it no longer silently falls back to the global leaderboard and no longer shows players like Alexander Bye in the wrong country view.
- Removed the temporary human-name selection heuristic after confirming the current schema does not store historical per-event player names.
- Fixed a strict TypeScript nullability regression in the latest-tournament matching logic that was breaking the PR 81 `Playwright E2E Tests` workflow during `next build`.

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
  - `Global Rank` now shows `EARTH` as the secondary line
  - `TopDeck` was renamed to `TopDeck Rank`
- Renamed the profile regions table from `State Assignment` to `Played Regions` and renamed its `Region` column to `State`.
- Updated `Seat Distribution` to include:
  - an `Overall` row above the per-seat rows
  - `Score:` percentages using `(wins + 0.2 × draws) / games`
  - a short static formula description under the section title
- Removed extra profile-page copy including:
  - `TopDeck Player Profile`
  - the old global/state-slice explainer under the player name
  - the old TopDeck/home-region explainer under the stat cards
  - the old helper blurbs under `Played Commanders` and `Played Regions`

## Matchup Algorithm

- Added documentation in [player-matchup-algorithm.md](/Users/alexanderlien/Documents/GitHub/cedh-research/docs/player-matchup-algorithm.md).
- Current algorithm:
  - draw weight: `0.2`
  - prior games: `20`
  - adjusted score uses Bayesian-style shrinkage toward the player baseline
  - no minimum-games gate for selecting a best/worst matchup
- Best matchup is the highest adjusted-score delta.
- Worst matchup is the lowest adjusted-score delta.

## Player Profile Data Fixes

- Fixed truncation in opponent matchup aggregation caused by fetching too many opponent rows in a single capped page.
- Paginated the remaining player-profile fetch paths that had the same class of bug:
  - event log fetches
  - commander usage fetches
  - raw tournament entry fetches
- Verified the Anthony GlacialCity / Albert Burse opponent counts are now symmetric at `11` games on both profile pages.

## Canonical Count Fix

- Updated the global/regional leaderboard SQL views so displayed games, wins, draws, losses, and last played date come from canonical global game-event aggregates.
- This removes drift between rating-table counters and the event stream while preserving the existing leaderboard ranking inputs.

## Backend Maintenance CI

- Replaced duplicated inline Python in [ci-backend-maintenance.yml](/Users/alexanderlien/Documents/GitHub/cedh-research/.github/workflows/ci-backend-maintenance.yml) with calls to the maintained [ci_backend_checks.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ci_backend_checks.py) script.
- Updated backend maintenance validation to match the currently deployed Supabase schema:
  - validates `regional_elo_regions` and `regional_elo_game_event_log` instead of stale `global_elo_*` aliases missing from the current schema cache
  - validates `regional_elo_state_activity` and `regional_elo_game_events` in the data-integrity pass
  - compares `regional_elo_player_stats` against primary `regional_elo_state_activity` rows for consistency instead of sampling the currently empty `regional_elo_leaderboard` view
- Removed a stale `country_key` dependency from the regional consistency sampler so the check still passes against older deployed `regional_elo_player_stats` definitions.

## Data Dictionary

- Updated [data_dictionary.md](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/docs/data_dictionary.md) for migration `20260409140000_fix_global_leaderboard_canonical_counts`.
- Documented that `global_elo_leaderboard` displayed record fields now come from canonical `global_elo_game_events` aggregates rather than rating-table counters.

## Testing / Validation

- `npm --workspace apps/web run test:ci`
- `npm --workspace apps/web run build`
- `npm run docs:check`
- `npm run docs:hygiene`
- `python3 packages/backend/src/ci_backend_checks.py views`
- `python3 packages/backend/src/ci_backend_checks.py data-integrity`
- `python3 packages/backend/src/ci_backend_checks.py regional-elo`
