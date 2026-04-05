# Release Lessons - 2026-04-05

## What broke
- The regional player drilldown mixed two different data sources on the same page.
- The summary cards (`Current Rank`, `Counted Games`, `Record`) read from `regional_elo_leaderboard`.
- The detailed game log reconstructed games from raw `tournament_entries`, `games`, and `game_participants`.
- Those sources drifted, so a player could show one record in the summary and a different record in the drilldown log.
- Production also spent time pointed at a stale Vercel alias, which made already-merged fixes appear missing.

## User impact
- The page presented conflicting truths for the same player and region.
- That undermines trust immediately because the first thing a user does is compare the top cards against the detailed log.
- For analytics products, visible inconsistency is interpreted as unreliability even when part of the data is technically correct.

## Root cause
- We allowed user-facing totals to be rendered from two independently computed paths.
- `regional_elo_ratings` persisted rating rows and stale counters.
- The drilldown reconstructed included games directly from canonical game rows.
- There was no CI invariant asserting that leaderboard summary fields and reconstructible detail agreed.
- Deployment aliasing in Vercel was not being explicitly verified after release.

## Fixes applied
- Added `regional_elo_player_stats` as the canonical per-region aggregate derived directly from `regional_elo_game_results`.
- Rewired `regional_elo_leaderboard` so `games_played`, `wins`, `draws`, `losses`, and `last_game_date` come from `regional_elo_player_stats`.
- Updated the player page to use the same canonical aggregate for its summary cards.
- Added regression coverage for player stat summarization and page-level rendering.
- Added a backend CI check that compares sampled leaderboard rows against canonical regional aggregates.

## Evidence
- Example player: Alex Lien (`CCIQroaCHHQi7EELyNXlHiHQiQy1`)
- California now matches exactly:
  - leaderboard: `28` games, `13-10-5`
  - canonical aggregate: `28` games, `13-10-5`

## Prevention
- Do not render user-facing totals from two different implementations on the same page.
- Treat the detailed drilldown as an explanation of the aggregate, not a second source of truth.
- Add CI invariants for all analytics summaries that users can manually reconcile.
- Include one human-readable evidence artifact in CI for critical analytics features.
- Verify the production alias target after release, not just that a deployment exists.

## QA checklist additions
- Compare one known player’s regional summary cards against the active row in `Regional Rankings`.
- Compare that same player’s summary cards against the canonical aggregate proof in CI.
- Spot-check one production URL and one preview URL to confirm they resolve to the same deployment when a release is expected to be live.
