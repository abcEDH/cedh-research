-- Harden the global Elo snapshot RPCs against the 8s authenticator timeout.
--
-- PostgREST connects as `authenticator` (statement_timeout=8s) and SET ROLE
-- service_role does not reset it, so these CTE-aggregation snapshots have been
-- riding under the 8s wall by luck. Under load (or as data grows) a single page
-- crosses 8s and is cancelled with 57014, failing the maintenance job before it
-- even reaches the recompute. Same root cause already fixed for the refresh RPCs
-- (20260618010000) and get_active_global_elo_player_ids; apply the same per-
-- function override here.
--
-- Only the paginated overloads exist in a clean schema built from these
-- migrations: 20260511235955 defines each function with DEFAULT args, and
-- default arguments do not create a separate bare-argument overload. The
-- maintenance job calls these paginated signatures via _rpc_fetch_all, so they
-- are the ones that matter. (ALTERing a bare signature here would fail with
-- "function does not exist" on a clean rebuild and abort the migration.)

ALTER FUNCTION public.get_global_elo_snapshot_before(timestamptz, integer, integer)
    SET statement_timeout TO '5min';

ALTER FUNCTION public.get_global_elo_state_activity_snapshot(integer, integer)
    SET statement_timeout TO '5min';

ALTER FUNCTION public.get_global_elo_player_meta_snapshot(integer, integer)
    SET statement_timeout TO '5min';
