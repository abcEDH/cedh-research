-- Migration: Restore commander_wow_mom view (latest week/month deltas)

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

GRANT SELECT ON commander_wow_mom TO anon, authenticated, service_role;
