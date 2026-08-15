-- Exclude tournaments with a future start_date from commander stats and
-- trend rollups. This is a schema-only fix (no data mutation): it makes the
-- views themselves ignore any tournament dated after "now", present or
-- future, rather than deleting a specific known-bad row. That keeps the
-- fix reproducible across environments and self-healing if another
-- future-dated tournament is ever ingested again despite the application-
-- level guard added in packages/backend/src/ingest.py.
--
-- Prompted by "Test Event for Dan and Noam" (topdeck_tid =
-- 'test-event-for-dan-and-noam'), a TopDeck.gg practice event ingested with
-- start_date = 2030-10-26 (~4 years in the future at ingestion time). Its 32
-- entries cleared commander_stats' player_count >= 32 threshold and created
-- a 2030-W43 / 2030-10 bucket in commander_weekly_trends /
-- commander_monthly_trends, both of which previously had no date bound at
-- all. Confirmed via audit that this was the only future-dated tournament in
-- the database; commander_weekly_trends_large / commander_monthly_trends_large
-- were checked separately and do not contain this event (its 32-player size
-- falls below whatever threshold gates the "_large" variants), and are left
-- untouched here since no migration in this repo currently defines them
-- (schema drift worth investigating separately).

-- View: commander_stats
-- total_entries/total_wins/total_losses/total_draws/avg_win_rate/
-- top_16_count/top_cut_count previously aggregated straight from
-- tournament_entries with no join to tournaments at all (only
-- tournaments_played depended on the existing player_count >= 32 join), so a
-- future-dated tournament's results were counted in every one of those
-- columns regardless of size. Adding a second LEFT JOIN scoped only to date
-- validity, and gating the whole row on it via WHERE, excludes invalid-date
-- entries from every aggregate while leaving the pre-existing
-- player_count >= 32 gating on tournaments_played/conversion columns
-- unchanged.
CREATE OR REPLACE VIEW commander_stats AS
SELECT
    c.id AS commander_id,
    c.name AS commander_name,
    c.archetype,
    c.color_identity,
    COUNT(DISTINCT te.id) AS total_entries,
    COUNT(DISTINCT t.id) AS tournaments_played,
    SUM(te.wins) AS total_wins,
    SUM(te.losses) AS total_losses,
    SUM(te.draws) AS total_draws,
    ROUND(AVG(te.win_rate), 4) AS avg_win_rate,
    COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_16) AS top_16_count,
    ROUND(
        COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_16)::NUMERIC /
        NULLIF(COUNT(DISTINCT te.id), 0),
        4
    ) AS conversion_rate_top_16,
    COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_cut) AS top_cut_count,
    ROUND(
        COUNT(DISTINCT te.id) FILTER (WHERE te.made_top_cut)::NUMERIC /
        NULLIF(COUNT(DISTINCT te.id), 0),
        4
    ) AS conversion_rate_top_cut
FROM commanders c
LEFT JOIN tournament_entries te ON c.id = te.commander_id
LEFT JOIN tournaments t_valid ON te.tournament_id = t_valid.id
LEFT JOIN tournaments t ON te.tournament_id = t.id AND t.player_count >= 32
WHERE te.id IS NULL OR t_valid.start_date::date <= CURRENT_DATE
GROUP BY c.id, c.name, c.archetype, c.color_identity;

-- Materialized views: commander_weekly_trends / commander_monthly_trends
-- (and the derived commander_wow_mom view). These use a plain INNER JOIN
-- to tournaments, so adding the date bound to the existing WHERE clause is
-- sufficient -- no restructuring needed. Materialized views must be dropped
-- and recreated to change their defining query; follow the same idempotent
-- drop pattern as 20260126010000_commander_trends_dates.sql.
DROP VIEW IF EXISTS commander_wow_mom;

DO $$
BEGIN
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
          AND c.relkind = 'm'
    ) THEN
        EXECUTE 'DROP MATERIALIZED VIEW public.commander_monthly_trends';
    END IF;
END;
$$;

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
  AND t.start_date::date <= CURRENT_DATE
GROUP BY c.id, c.name, date_trunc('week', t.start_date);

CREATE UNIQUE INDEX idx_commander_weekly_trends_pk
ON commander_weekly_trends(commander_id, week_start_date);

CREATE INDEX idx_commander_weekly_trends_commander
ON commander_weekly_trends(commander_id);

CREATE INDEX idx_commander_weekly_trends_week_start
ON commander_weekly_trends(week_start_date);

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
  AND t.start_date::date <= CURRENT_DATE
GROUP BY c.id, c.name, date_trunc('month', t.start_date);

CREATE UNIQUE INDEX idx_commander_monthly_trends_pk
ON commander_monthly_trends(commander_id, month_start_date);

CREATE INDEX idx_commander_monthly_trends_commander
ON commander_monthly_trends(commander_id);

CREATE INDEX idx_commander_monthly_trends_month_start
ON commander_monthly_trends(month_start_date);

-- Restore commander_wow_mom unchanged -- it derives entirely from the two
-- materialized views above, so it inherits the date exclusion automatically.
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

-- Grants (materialized views lose grants on drop/recreate)
GRANT SELECT ON commander_weekly_trends TO anon, authenticated, service_role;
GRANT SELECT ON commander_monthly_trends TO anon, authenticated, service_role;
GRANT SELECT ON commander_wow_mom TO anon, authenticated, service_role;
