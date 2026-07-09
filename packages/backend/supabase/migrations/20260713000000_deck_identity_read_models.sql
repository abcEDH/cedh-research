-- Generalized multi-game read models (ADR 0015).
--
-- deck_identity_stats and meta_share_weekly are the game-agnostic counterparts
-- of commander_stats / commander_meta_monthly: every row carries (game, format)
-- so the multi-game frontend can serve Riftbound, Gundam TCG, and Yu-Gi-Oh
-- alongside cEDH from the same surfaces.

-- ============================================================================
-- VIEW: deck_identity_stats
-- ============================================================================

CREATE OR REPLACE VIEW deck_identity_stats AS
SELECT t.game, t.format, c.id AS identity_id, c.name, c.identity_kind,
       COUNT(DISTINCT te.id) AS entries,
       COUNT(DISTINCT t.id) AS tournaments_played,
       COALESCE(SUM(te.wins), 0) AS wins,
       COALESCE(SUM(te.losses), 0) AS losses,
       COALESCE(SUM(te.draws), 0) AS draws,
       COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_cut) AS top_cut_count,
       ROUND(AVG(te.win_rate)::numeric, 4) AS avg_win_rate
FROM commanders c
JOIN tournament_entries te ON te.commander_id = c.id
JOIN tournaments t ON te.tournament_id = t.id
GROUP BY t.game, t.format, c.id, c.name, c.identity_kind;

COMMENT ON VIEW deck_identity_stats IS
    'Per-(game, format) performance summary for each deck identity (commander / legend / leader / archetype).';

-- Views default to security definer semantics; follow the 20260328000000 /
-- 20260508000000 convention.
ALTER VIEW deck_identity_stats SET (security_invoker = true);

GRANT SELECT ON deck_identity_stats TO anon, authenticated;

-- ============================================================================
-- MATERIALIZED VIEW: meta_share_weekly
-- ============================================================================

CREATE MATERIALIZED VIEW meta_share_weekly AS
SELECT t.game, t.format, date_trunc('week', t.start_date)::date AS week,
       te.commander_id AS identity_id, COUNT(*) AS entries,
       (COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY t.game, t.format, date_trunc('week', t.start_date)))::numeric(8,6) AS meta_share
FROM tournament_entries te JOIN tournaments t ON te.tournament_id = t.id
WHERE t.start_date IS NOT NULL
GROUP BY t.game, t.format, date_trunc('week', t.start_date), te.commander_id;

-- Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY.
CREATE UNIQUE INDEX idx_meta_share_weekly_pk
ON meta_share_weekly(game, format, week, identity_id);

COMMENT ON MATERIALIZED VIEW meta_share_weekly IS
    'Weekly meta share per deck identity within each (game, format); refresh via refresh_meta_share_weekly().';

GRANT SELECT ON meta_share_weekly TO anon, authenticated, service_role;

-- ============================================================================
-- FUNCTION: refresh_meta_share_weekly
-- ============================================================================
-- Follows the refresh_card_frequencies / refresh_card_performance pattern
-- (20260121000000 / 20260618193900): concurrent refresh with an explicit
-- statement_timeout so the PostgREST authenticator's 8s session default cannot
-- cancel it, SECURITY DEFINER with a pinned search_path, service_role-only.

CREATE OR REPLACE FUNCTION refresh_meta_share_weekly()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
SET statement_timeout TO '30min'
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY meta_share_weekly;
END;
$$;

GRANT EXECUTE ON FUNCTION refresh_meta_share_weekly() TO service_role;

COMMENT ON FUNCTION refresh_meta_share_weekly IS 'Refreshes the meta_share_weekly materialized view';
