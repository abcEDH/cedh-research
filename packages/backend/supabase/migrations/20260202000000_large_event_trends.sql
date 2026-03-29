-- Migration: Commander weekly/monthly trends for large events (65+ players)

DROP VIEW IF EXISTS commander_weekly_trends_large;
DROP VIEW IF EXISTS commander_monthly_trends_large;
DROP VIEW IF EXISTS commander_stats_large;
DROP MATERIALIZED VIEW IF EXISTS commander_weekly_trends_large;
DROP MATERIALIZED VIEW IF EXISTS commander_monthly_trends_large;

-- VIEW: Commander performance summary (65+ players)
CREATE OR REPLACE VIEW commander_stats_large AS
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
LEFT JOIN tournaments t ON te.tournament_id = t.id AND t.player_count >= 65
GROUP BY c.id, c.name, c.archetype, c.color_identity;

-- MATERIALIZED VIEW: Commander performance by ISO week (65+ players)
CREATE MATERIALIZED VIEW commander_weekly_trends_large AS
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
WHERE t.player_count >= 65
  AND c.name <> 'Unknown Commander'
GROUP BY c.id, c.name, date_trunc('week', t.start_date);

CREATE UNIQUE INDEX idx_commander_weekly_trends_large_pk
ON commander_weekly_trends_large(commander_id, week_start_date);

CREATE INDEX idx_commander_weekly_trends_large_commander
ON commander_weekly_trends_large(commander_id);

CREATE INDEX idx_commander_weekly_trends_large_week_start
ON commander_weekly_trends_large(week_start_date);

-- MATERIALIZED VIEW: Commander performance by month (65+ players)
CREATE MATERIALIZED VIEW commander_monthly_trends_large AS
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
WHERE t.player_count >= 65
  AND c.name <> 'Unknown Commander'
GROUP BY c.id, c.name, date_trunc('month', t.start_date);

CREATE UNIQUE INDEX idx_commander_monthly_trends_large_pk
ON commander_monthly_trends_large(commander_id, month_start_date);

CREATE INDEX idx_commander_monthly_trends_large_commander
ON commander_monthly_trends_large(commander_id);

CREATE INDEX idx_commander_monthly_trends_large_month_start
ON commander_monthly_trends_large(month_start_date);
