# PR 127 Summary

## Summary

This PR combines the recent regional Elo frontend work with a broader data-normalization and repair pass across the backend. It adds a dedicated player-vs-player page, tightens leaderboard and tournament-likelihood commander forecasting, introduces TopDeck Elo support, and hardens ingest so malformed or illegal commander pairings no longer enter the database.

The backend side of the PR is mostly about data quality and maintainability:

- normalizes commander names before write time
- strips DFC back faces from stored commander labels
- rewrites Stranger Things names to their in-universe equivalents
- rejects illegal two-card commander pairings by mapping them to `Unknown Commander`
- canonicalizes legal partner pair ordering from a generated legality reference
- adds repair, rebuild, import, and review scripts used to bring Supabase into line with the new rules

Changed files in PR 127:

- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/page.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/page.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/vs/[opponentTopdeckId]/page.tsx)
- [player-log-data.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/player-log-data.ts)
- [regional-leaderboard-table.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/regional-leaderboard-table.tsx)
- [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/tournament-likelihood/page.tsx)
- [tournament-analysis-tables.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/tournament-likelihood/tournament-analysis-tables.tsx)
- [meta-prep.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/meta-prep.ts)
- [topdeck-elo.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck-elo.ts)
- [topdeck.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck.ts)
- [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py)
- [generate_legal_commander_pairings.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/generate_legal_commander_pairings.py)
- [generate_missing_partner_order_review.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/generate_missing_partner_order_review.py)
- [rebuild_player_commander_profiles.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_player_commander_profiles.py)
- [rebuild_global_elo_tables.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_global_elo_tables.py)
- [import_topdeck_player_elos.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/import_topdeck_player_elos.py)
- [repair_unknown_commanders_from_decklists.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/repair_unknown_commanders_from_decklists.py)
- [sweep_partner_commander_order.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/sweep_partner_commander_order.py)
- [legal_commander_pairings.json](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/data/legal_commander_pairings.json)
- [test_ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/tests/test_ingest.py)

GitHub source checked against the live PR diff:
- [PR 127 Files Changed](https://github.com/abcEDH/cedh-research/pull/127/files)

## Regional Elo Frontend

- Adds the dedicated head-to-head route at [page.tsx](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/vs/[opponentTopdeckId]/page.tsx) and rewires opponent links from the player profile to use it.
- Adds shared-log loading in [player-log-data.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/app/regional-elo/player/[topdeckId]/player-log-data.ts) so the player profile and matchup page use the same canonical event history path.
- Expands the matchup page with mirrored records, commander-specific summary cards, collapsed chronological game history, per-pod seat and commander context, and winner highlighting.
- Tightens the leaderboard and player-profile surfaces around TopDeck-based ranking and matchup navigation.
- Updates tournament likelihood and commander forecasting UI to use the same active-commander selection logic as the regional Elo surfaces.

## TopDeck Elo And Commander Forecasting

- Adds [topdeck-elo.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/topdeck-elo.ts) and supporting leaderboard wiring so TopDeck Elo snapshots can be surfaced alongside the existing regional/global Elo views.
- Updates commander-recommendation weighting in [meta-prep.ts](/Users/alexanderlien/Documents/GitHub/cedh-research/apps/web/src/lib/meta-prep.ts), [rebuild_player_commander_profiles.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_player_commander_profiles.py), and [regional_elo.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/regional_elo.py) to use a `28`-day half-life instead of the earlier shorter recency window.
- Improves tournament-likelihood tables with pagination and richer field-share output so larger event forecasts remain usable.
- Adds [import_topdeck_player_elos.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/import_topdeck_player_elos.py) plus [20260415020000_topdeck_player_elos.sql](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/supabase/migrations/20260415020000_topdeck_player_elos.sql) to support importing the current TopDeck Elo snapshot into Supabase.

## Commander Normalization And Legality

- Hardens [ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/ingest.py) so commander payloads are normalized before upsert:
  - strips escaped apostrophes
  - removes DFC back faces from commander names
  - rewrites Stranger Things Secret Lair names to their in-universe equivalents
  - canonicalizes legal pair order before building stored pair names
  - maps illegal two-card commander pairings to `Unknown Commander`
- Adds [generate_legal_commander_pairings.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/generate_legal_commander_pairings.py) to build [legal_commander_pairings.json](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/data/legal_commander_pairings.json) from Scryfall oracle data as the canonical legality and ordering reference.
- Extends [test_ingest.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/tests/test_ingest.py) to cover:
  - apostrophe cleanup
  - DFC stripping
  - Stranger Things alias rewrites
  - legal-pair canonical ordering
  - illegal-pair fallback to `Unknown Commander`

## Partner Order Review Workflow

- Replaces the old archival partner community review CSV with generated review tooling.
- Adds [generate_missing_partner_order_review.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/generate_missing_partner_order_review.py) to emit a review queue for legal partner pairings that are not yet represented in stored commander rows.
- The generated review file includes direct search URLs for Reddit-focused search, X, and general web search so missing community ordering can be reviewed from discussion sources instead of inferred from TopDeck deck entry order.
- Updates [sweep_partner_commander_order.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/sweep_partner_commander_order.py) and ingest normalization so canonical community ordering is enforced both in historical cleanup passes and on future ingest.

## Data Repair And Rebuild Tooling

- Adds or expands backend maintenance scripts used to reconcile Supabase with the new data rules:
  - [rebuild_global_elo_tables.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/rebuild_global_elo_tables.py)
  - [recompute_global_elo_all_games.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/recompute_global_elo_all_games.py)
  - [repair_bad_game_outcomes.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/repair_bad_game_outcomes.py)
  - [repair_participant_outcome_mismatches.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/repair_participant_outcome_mismatches.py)
  - [repair_unknown_commanders_from_decklists.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/repair_unknown_commanders_from_decklists.py)
  - [backfill_flat_firestore_games.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_flat_firestore_games.py)
  - [backfill_topdeck_firestore_outcomes.py](/Users/alexanderlien/Documents/GitHub/cedh-research/packages/backend/src/backfill_topdeck_firestore_outcomes.py)
- Keeps the player-commander profile rebuild aligned with the new commander normalization rules so active commander output stays consistent between ingest-time writes and derived profile tables.

## Live Data Follow-Up

- The supporting cleanup work behind this PR also refreshed live Supabase data so existing rows match the new normalization rules.
- Follow-up maintenance included:
  - refreshing recent TopDeck tournament ingest
  - rebuilding player commander profiles and global Elo profile-facing tables
  - importing the latest TopDeck Elo snapshot
  - remapping illegal stored two-card commander rows to `Unknown Commander`
  - merging reversed or alias-based commander rows into canonical in-universe names and canonical legal-pair ordering

## Validation

Compared this document against the live GitHub diff for [PR 127](https://github.com/abcEDH/cedh-research/pull/127/files).

Verified locally with:

```bash
python3 -m unittest packages/backend/tests/test_ingest.py
python3 packages/backend/src/generate_legal_commander_pairings.py
python3 packages/backend/src/generate_missing_partner_order_review.py
python3 packages/backend/src/rebuild_player_commander_profiles.py
npm run build --workspace apps/web
```
