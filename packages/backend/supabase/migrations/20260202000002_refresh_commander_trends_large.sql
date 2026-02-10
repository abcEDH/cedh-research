-- Migration: Refresh function covers large-event commander trends

CREATE OR REPLACE FUNCTION refresh_commander_trends()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY commander_weekly_trends;
    REFRESH MATERIALIZED VIEW CONCURRENTLY commander_monthly_trends;
    REFRESH MATERIALIZED VIEW CONCURRENTLY commander_weekly_trends_large;
    REFRESH MATERIALIZED VIEW CONCURRENTLY commander_monthly_trends_large;
END;
$$;
