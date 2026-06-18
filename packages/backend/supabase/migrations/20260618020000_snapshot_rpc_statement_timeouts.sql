-- Harden the global Elo snapshot RPCs against the 8s authenticator timeout.
--
-- PostgREST connects as `authenticator` (statement_timeout=8s) and SET ROLE
-- service_role does not reset it, so these CTE-aggregation snapshots have been
-- riding under the 8s wall by luck. Under load (or as data grows) a single page
-- crosses 8s and is cancelled with 57014, failing the maintenance job before it
-- even reaches the recompute. Same root cause already fixed for the refresh RPCs
-- (20260618010000) and get_active_global_elo_player_ids; apply the same per-
-- function override here. Covers both overloads of each (paginated + bare).

ALTER FUNCTION public.get_global_elo_snapshot_before(timestamptz)
    SET statement_timeout TO '5min';
ALTER FUNCTION public.get_global_elo_snapshot_before(timestamptz, integer, integer)
    SET statement_timeout TO '5min';

ALTER FUNCTION public.get_global_elo_state_activity_snapshot()
    SET statement_timeout TO '5min';
ALTER FUNCTION public.get_global_elo_state_activity_snapshot(integer, integer)
    SET statement_timeout TO '5min';

ALTER FUNCTION public.get_global_elo_player_meta_snapshot()
    SET statement_timeout TO '5min';
ALTER FUNCTION public.get_global_elo_player_meta_snapshot(integer, integer)
    SET statement_timeout TO '5min';
