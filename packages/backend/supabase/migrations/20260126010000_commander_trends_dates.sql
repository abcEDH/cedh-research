-- Migration: Add week/month start dates to commander trends

-- Drop in dependency order for idempotency (handle view vs materialized view)
DROP VIEW IF EXISTS commander_wow_mom;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'commander_weekly_trends'
          AND c.relkind = 'v'
    ) THEN
        EXECUTE 'DROP VIEW public.commander_weekly_trends';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'commander_weekly_trends'
          AND c.relkind = 'm'
    ) THEN
        EXECUTE 'DROP MATERIALIZED VIEW public.commander_weekly_trends';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'commander_monthly_trends'
          AND c.relkind = 'v'
    ) THEN
        EXECUTE 'DROP VIEW public.commander_monthly_trends';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'commander_monthly_trends'
          AND c.relkind = 'm'
    ) THEN
        EXECUTE 'DROP MATERIALIZED VIEW public.commander_monthly_trends';
    END IF;
END;
$$;

-- MATERIALIZED VIEW: Commander performance by ISO week (with start date)
CREATE MATERIALIZED VIEW commander_weekly_trends AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    date_trunc('week', t.start_date)::date AS week_start_date,
    to_char(date_trunc('week', t.start_date), 'IYYY-"W"IW') AS week_key,
    COUNT(*) AS entries,
    SUM(te.wins) AS wins,
    SUM(te.losses) AS losses,
    SUM(te.draws) AS draws,
    ROUND(
        SUM(te.wins)::numeric / NULLIF(SUM(te.wins + te.losses + te.draws), 0),
        4
    ) AS win_rate
FROM tournament_entries te
JOIN tournaments t ON te.tournament_id = t.id
JOIN commanders c ON te.commander_id = c.id
WHERE t.player_count >= 32
  AND c.name <> 'Unknown Commander'
GROUP BY c.id, c.name, date_trunc('week', t.start_date);

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_commander_weekly_trends_pk
ON commander_weekly_trends(commander_id, week_start_date);

CREATE INDEX idx_commander_weekly_trends_commander
ON commander_weekly_trends(commander_id);

CREATE INDEX idx_commander_weekly_trends_week_start
ON commander_weekly_trends(week_start_date);

-- MATERIALIZED VIEW: Commander performance by month (with start date)
CREATE MATERIALIZED VIEW commander_monthly_trends AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    date_trunc('month', t.start_date)::date AS month_start_date,
    to_char(date_trunc('month', t.start_date), 'YYYY-MM') AS month_key,
    COUNT(*) AS entries,
    SUM(te.wins) AS wins,
    SUM(te.losses) AS losses,
    SUM(te.draws) AS draws,
    ROUND(
        SUM(te.wins)::numeric / NULLIF(SUM(te.wins + te.losses + te.draws), 0),
        4
    ) AS win_rate
FROM tournament_entries te
JOIN tournaments t ON te.tournament_id = t.id
JOIN commanders c ON te.commander_id = c.id
WHERE t.player_count >= 32
  AND c.name <> 'Unknown Commander'
GROUP BY c.id, c.name, date_trunc('month', t.start_date);

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX idx_commander_monthly_trends_pk
ON commander_monthly_trends(commander_id, month_start_date);

CREATE INDEX idx_commander_monthly_trends_commander
ON commander_monthly_trends(commander_id);

CREATE INDEX idx_commander_monthly_trends_month_start
ON commander_monthly_trends(month_start_date);

-- VIEW: Latest WoW/MoM deltas per commander (ordered by start dates)
CREATE OR REPLACE VIEW commander_wow_mom AS
WITH weekly AS (
    SELECT
        commander_id,
        commander_name,
        week_start_date,
        week_key,
        entries,
        win_rate,
        LAG(entries) OVER (
            PARTITION BY commander_id
            ORDER BY week_start_date
        ) AS prev_entries,
        LAG(win_rate) OVER (
            PARTITION BY commander_id
            ORDER BY week_start_date
        ) AS prev_win_rate,
        ROW_NUMBER() OVER (
            PARTITION BY commander_id
            ORDER BY week_start_date DESC
        ) AS rn
    FROM commander_weekly_trends
),
monthly AS (
    SELECT
        commander_id,
        commander_name,
        month_start_date,
        month_key,
        entries,
        win_rate,
        LAG(entries) OVER (
            PARTITION BY commander_id
            ORDER BY month_start_date
        ) AS prev_entries,
        LAG(win_rate) OVER (
            PARTITION BY commander_id
            ORDER BY month_start_date
        ) AS prev_win_rate,
        ROW_NUMBER() OVER (
            PARTITION BY commander_id
            ORDER BY month_start_date DESC
        ) AS rn
    FROM commander_monthly_trends
)
SELECT
    w.commander_id,
    w.commander_name,
    w.week_start_date AS latest_week_start_date,
    w.week_key AS latest_week_key,
    w.entries AS week_entries,
    w.win_rate AS week_win_rate,
    ROUND(
        (w.entries - w.prev_entries)::numeric / NULLIF(w.prev_entries, 0) * 100,
        2
    ) AS week_entries_change_pct,
    ROUND(
        (w.win_rate - w.prev_win_rate) * 100,
        2
    ) AS week_win_rate_change_pp,
    m.month_start_date AS latest_month_start_date,
    m.month_key AS latest_month_key,
    m.entries AS month_entries,
    m.win_rate AS month_win_rate,
    ROUND(
        (m.entries - m.prev_entries)::numeric / NULLIF(m.prev_entries, 0) * 100,
        2
    ) AS month_entries_change_pct,
    ROUND(
        (m.win_rate - m.prev_win_rate) * 100,
        2
    ) AS month_win_rate_change_pp
FROM weekly w
LEFT JOIN monthly m
    ON m.commander_id = w.commander_id
   AND m.rn = 1
WHERE w.rn = 1;

-- Helper: refresh both commander trend materialized views
CREATE OR REPLACE FUNCTION refresh_commander_trends()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY commander_weekly_trends;
    REFRESH MATERIALIZED VIEW CONCURRENTLY commander_monthly_trends;
END;
$$;

-- Grants
GRANT SELECT ON commander_weekly_trends TO anon, authenticated, service_role;
GRANT SELECT ON commander_monthly_trends TO anon, authenticated, service_role;
GRANT SELECT ON commander_wow_mom TO anon, authenticated, service_role;
