# PR 110 Summary

## Summary

This PR fixes multiple data-ingest and cache-invalidation issues that were leaving commander data stale or incorrectly normalized in player profiles and Tournament Prep.

The main fixes are:

- normalize TopDeck decklists that arrive with escaped newlines so commander extraction works
- add a reusable rebuild for `player_commander_profiles`
- add a repair script for `Unknown Commander` entries that can now be re-parsed from stored decklists
- add canonical partner-order normalization so repaired commander pairs match existing project ordering
- prune stale `player_commander_profiles` rows that no longer have any qualifying known-commander history
- normalize escaped apostrophes in commander names so rows like `Kraum, Ludevic\\'s Opus / Tymna the Weaver` merge into their canonical forms
- add a sweep script that can merge duplicate partner-pair commander rows back into the canonical rows
- fix Tournament Prep event-URL fallback start times by reading TopDeck event timing from the public Firestore event document instead of hardcoding an empty start date
- invalidate the player-profile and Tournament Prep caches so repaired data appears in the UI
- add a skip-existing ingestion mode so large backfills do not waste time reprocessing tournaments already in Supabase

Changed files in PR 110:

- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/tournament-likelihood/page.tsx)
- [topdeck.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck.ts)
- [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py)
- [rebuild_player_commander_profiles.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_player_commander_profiles.py)
- [repair_unknown_commanders_from_decklists.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/repair_unknown_commanders_from_decklists.py)
- [sweep_partner_commander_order.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/sweep_partner_commander_order.py)

GitHub source checked against the live PR diff:
- [PR 110 Files Changed](https://github.com/abcEDH/cedh-research/pull/110/files)

## Ingest Fixes

- Adds `PARTNER_ORDER_OVERRIDES` to [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py) so partner pairs use the project’s canonical display order instead of simple alphabetical order.
- Adds `normalize_partner_order()` and updates `normalize_commander_name()` to use canonical pair ordering for partner decks.
- Fixes `extract_commanders()` so TopDeck decklists with literal escaped newlines like `\\n` and `\\r\\n` are normalized before parsing the commander section.
- Adds `fetch_existing_tids()` so the ingester can efficiently check which TopDeck tournament IDs already exist in Supabase.
- Adds the missing manifest/backfill CLI arguments used by the older `--tids-file` path:
  - `--tids-file`
  - `--names-file`
  - `--resolve-days`
  - `--tids-out`
  - `--selected-tids-out`
  - `--skip-existing-tids`
  - `--only-failed-from-run-key`
  - `--batch-size`
  - `--batch-index`
  - `--run-key`
  - `--record-backfill`
  - `--start-date`
  - `--end-date`
- Adds `--skip-existing-tournaments` to skip tournaments whose `topdeck_tid` is already present in Supabase.
- Applies `--skip-existing-tournaments` in:
  - single-tournament mode
  - `--tids-file` mode
  - `--days` search mode
- Initializes `db_client = None` during setup so `--direct` ingest runs do not fail on cleanup if the direct client was never created.

## Player Commander Profile Rebuild

- Adds [rebuild_player_commander_profiles.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_player_commander_profiles.py) as a repo-backed rebuild for the precomputed `player_commander_profiles` table.
- Rebuild logic matches the app’s commander-forecast behavior:
  - `6` month primary lookback
  - `12` month fallback lookback
  - minimum `2` primary entries before falling back
  - `15` day recency half-life
- Reads historical usage from `tournament_entries` joined to:
  - `players`
  - `commanders`
  - `tournaments`
- Excludes `Unknown Commander`.
- Builds top-three commander predictions per player with:
  - `entries`
  - `share`
  - `weighted_share`
  - `prediction_share`
  - `prediction_score`
  - `latest_date`
  - `latest_decklist_url`
- Stores summary fields including:
  - `active_commander`
  - `active_commander_entries`
  - `active_commander_prediction_score`
  - `total_entries`
  - `latest_commander`
  - `latest_commander_date`
  - `latest_decklist_url`
- Supports direct Postgres reads through `SUPABASE_DB_URL` and falls back to Supabase REST when direct DB access is unavailable.
- Uses keyset pagination on `tournament_entries.id` for the REST path so the rebuild can complete on large datasets.
- Deletes stale `player_commander_profiles` rows before upserting the rebuilt set, so old profile rows are removed when a player no longer has any qualifying known-commander source rows.
- Upserts rebuilt rows into `player_commander_profiles` on `player_id`.

## Unknown Commander Repair

- Adds [repair_unknown_commanders_from_decklists.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/repair_unknown_commanders_from_decklists.py).
- Reads `tournament_entries` whose joined commander row is `Unknown Commander`.
- Re-parses stored `decklist_text` with the fixed `extract_commanders()` logic.
- Converts parsed commander names through the same canonical normalization used by ingest.
- Resolves commander IDs by scanning the `commanders` table and matching in Python, instead of relying on a fragile `in.(...)` filter against names containing commas or slashes.
- Updates `tournament_entries.commander_id` in place through Supabase REST.
- Retries transient patch failures for connection and timeout errors.

## Partner Order Sweep

- Updates [sweep_partner_commander_order.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/sweep_partner_commander_order.py) to reuse the canonical partner ordering from [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py).
- Uses TopDeck deck-page observations when no explicit override exists.
- Adds helper operations to:
  - repoint `tournament_entries` from a duplicate commander row to the canonical commander row
  - update a commander row’s `name` and `commander_names`
  - delete duplicate commander rows after repointing
- Writes a CSV report for the sweep run.
- Supports merging duplicate partner-pair commander rows when both canonical and non-canonical names already exist in Supabase.

## Web Cache Invalidation

- Bumps the cached player-profile fetch keys in [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx):
  - `regional-player-profile-summary-v1` -> `regional-player-profile-summary-v2`
  - `regional-player-achievements-v1` -> `regional-player-achievements-v2`
  - `regional-player-commander-usage-v1` -> `regional-player-commander-usage-v2`
  - `regional-player-event-logs-v1` -> `regional-player-event-logs-v2`
- Bumps the Tournament Prep analysis cache key in [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/tournament-likelihood/page.tsx):
  - `tournament-likelihood-analysis-v22` -> `tournament-likelihood-analysis-v25`
- Adds a follow-up Tournament Prep cache bump after the escaped-name cleanup:
  - `tournament-likelihood-analysis-v25` -> `tournament-likelihood-analysis-v26`

These cache-key changes force refreshed reads after repairing commander rows and rebuilding `player_commander_profiles`.

## Tournament Prep Event Timing Fallback

- Updates [topdeck.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck.ts) so the no-`TOPDECK_API_KEY` fallback path no longer hardcodes `startDate: ""`.
- Adds a Firestore-backed event timing fallback for TopDeck event URLs using TopDeck's public Firebase project:
  - project: `eminence-1b40b`
  - collection: `otherEvents/{slug}`
- Reads `startDate` and `endDate` from the Firestore event document and uses that timestamp in the returned tournament payload.
- This fixes Tournament Prep event pages that were showing `Unknown start time` even though the TopDeck event page displayed a start time.
- Verified against `breach-the-bay-2`:
  - TopDeck Firestore document returned `startDate = 1787410800`
  - local build now has access to the real event start time instead of an empty value

## Data Repair Work Done With These Changes

Using the scripts in this PR:

- reran the unknown-commander repair after fixing decklist parsing and commander-name resolution
- rebuilt `player_commander_profiles` from the corrected tournament-entry data
- normalized existing partner-pair commander rows to canonical order
- merged `9` duplicate partner commander rows into their canonical rows
- repointed affected `tournament_entries` to the canonical commander IDs
- rebuilt `player_commander_profiles` again after the partner-order merge
- fixed the rebuild process so it deletes stale profile rows instead of leaving outdated commander summaries behind
- deleted `336` stale `player_commander_profiles` rows during the pruning rebuild
- normalized commander names containing escaped apostrophes and merged them into clean canonical rows
- updated `5` escaped-name commander rows in place
- merged `17` escaped-name commander rows into existing clean commander rows
- rebuilt `player_commander_profiles` again after the escaped-name cleanup

Verified outcomes:

- duplicate partner-pair commander rows remaining in Supabase: `0`
- canonical rows such as `Rograkh, Son of Rohgahh / Ishai, Ojutai Dragonspeaker` and `Tymna the Weaver / Thrasios, Triton Hero` remain
- non-canonical duplicates such as `Ishai, Ojutai Dragonspeaker / Rograkh, Son of Rohgahh` and `Thrasios, Triton Hero / Tymna the Weaver` were removed
- commander rows with escaped apostrophes remaining in Supabase: `0`
- Sam Black (`8v3PyNSil7X6PhFayKUBFa60x973`) now resolves correctly in `player_commander_profiles` with:
  - `active_commander = Rograkh, Son of Rohgahh / Thrasios, Triton Hero`
  - `latest_commander = Rograkh, Son of Rohgahh / Thrasios, Triton Hero`
  - `latest_commander_date = 2026-04-18`
  - `Misplay on the Lake` reflected as the latest Rog/Thras decklist
- Eric V - Tap For Hope (`ihW7aupIQ5TV7qfJl9vJPHJjQXi1`) now resolves correctly with:
  - recent `tournament_entries` using `Tymna the Weaver / Kraum, Ludevic's Opus`
  - `player_commander_profiles.active_commander = Tymna the Weaver / Kraum, Ludevic's Opus`
  - `player_commander_profiles.latest_commander = Tymna the Weaver / Kraum, Ludevic's Opus`
  - the prior escaped-name variant removed from source data

## Ingestion Backfill Follow-Up

The new `--skip-existing-tournaments` flag was used to reduce redundant work during backfills:

- last `30` days:
  - TopDeck search returned `904` tournaments
  - `144` were new inserts by `created_at`
  - about `760` were already present and would be good candidates to skip on repeat runs
- last `6` months backfill check:
  - `4443` unique TopDeck tournament IDs found
  - `4437` already existed
  - `6` were missing and ingested
- historical pre-6-month window check:
  - `8263` unique TopDeck tournament IDs found
  - `8259` already existed
  - `4` were missing and ingested

## Validation

Compared this document against the live GitHub diff for [PR 110](https://github.com/abcEDH/cedh-research/pull/110/files).

Verified syntax locally with:

```bash
python3 -m py_compile \
  packages/backend/src/ingest.py \
  packages/backend/src/rebuild_player_commander_profiles.py \
  packages/backend/src/repair_unknown_commanders_from_decklists.py \
  packages/backend/src/sweep_partner_commander_order.py
```

Operational checks completed:

- `repair_unknown_commanders_from_decklists.py` completed successfully after the ingest and lookup fixes
- `rebuild_player_commander_profiles.py` completed successfully and upserted `26,965` profile rows from `110,294` qualifying usage rows
- the pruning rebuild deleted `336` stale profile rows before the upsert
- partner-order duplicate check after the sweep returned `0` duplicate partner-pair commander keys
- escaped-apostrophe commander cleanup completed with `5` direct updates and `17` merges
- `npm run build --workspace apps/web` passed after the Tournament Prep event-timing fallback change
