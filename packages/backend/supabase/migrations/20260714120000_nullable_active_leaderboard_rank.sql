-- Allow `rank` to be NULL on global_elo_active_leaderboard, mirroring the
-- existing nullable `topdeck_elo_rank` column added in
-- 20260501000000_regional_elo_leaderboard_topdeck_fields.sql.
--
-- Rows for players who fail the rank-eligibility gate in
-- build_active_leaderboard_rows() (zero games, or no tournament in the last
-- RANK_ACTIVITY_WINDOW_DAYS) previously still received a real, non-null
-- `rank` -- just sorted after every eligible row. Several apps/web read
-- paths fall back to that `rank` whenever `topdeck_elo_rank` is null (e.g.
-- a player's own profile page), so an inactive/zero-game player could still
-- see a real-looking rank badge, defeating the activity-eligibility fix
-- from PR #263 (Codex P2 review finding). `rank` is now nullable so
-- ineligible rows can receive `rank = NULL` just like `topdeck_elo_rank`.

ALTER TABLE public.global_elo_active_leaderboard
  ALTER COLUMN rank DROP NOT NULL;
