-- Retire backend surfaces for deleted product pages.
-- These objects supported the removed /cards, /turn-order, and /survival routes
-- or legacy internal diagnostics that are no longer part of the supported product.

DROP FUNCTION IF EXISTS get_commanders_for_card(TEXT);

DROP MATERIALIZED VIEW IF EXISTS commander_seat_stats;

DROP VIEW IF EXISTS survival_summary;
DROP VIEW IF EXISTS player_survival_stats;
DROP VIEW IF EXISTS commander_tournament_depth;
DROP VIEW IF EXISTS commander_survival_curve;
DROP VIEW IF EXISTS seat_survival_by_round;
DROP VIEW IF EXISTS seat_survival_by_commander;
DROP VIEW IF EXISTS round_win_rates;
DROP VIEW IF EXISTS seat_position_stats;
