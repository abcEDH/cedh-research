# Supabase View & RPC Inventory

This document maps backend surfaces to their consumers to guide deprecation and maintenance.

=== INVENTORY ===

## Views
- **commander_card_report**: Used by Backend: card_frequency.py, Frontend: lib/commanders/fetchers.ts
- **commander_first_appearances**: UNUSED
- **commander_head_to_head**: UNUSED
- **commander_meta_monthly**: UNUSED
- **commander_momentum**: UNUSED
- **commander_stats**: Used by Frontend: app/page.tsx, Backend: snapshot_analysis.py, Frontend: app/commanders/page.tsx, Frontend: lib/commanders/fetchers.ts, Frontend: components/home-search-bar.tsx, Frontend: app/trap-spice/page.tsx
- **commander_survival_curve**: UNUSED
- **commander_tournament_depth**: UNUSED
- **commander_wow_mom**: UNUSED
- **global_elo_data_validity**: UNUSED
- **global_elo_game_event_log**: UNUSED
- **global_elo_game_results**: UNUSED
- **global_elo_leaderboard**: UNUSED
- **global_elo_player_stats**: UNUSED
- **global_elo_primary_state_assignments**: UNUSED
- **global_elo_regions**: Used by Frontend: app/regional-elo/page.tsx
- **latest_analysis**: UNUSED
- **only**: UNUSED
- **player_commander_entries**: UNUSED
- **player_seat_distribution**: UNUSED
- **player_survival_stats**: UNUSED
- **player_tournament_journey**: UNUSED
- **pod_composition**: UNUSED
- **regional_elo_active_leaderboard**: UNUSED
- **regional_elo_data_validity**: UNUSED
- **regional_elo_game_event_log**: UNUSED
- **regional_elo_game_events**: UNUSED
- **regional_elo_game_results**: UNUSED
- **regional_elo_leaderboard**: UNUSED
- **regional_elo_player_profile_summaries**: UNUSED
- **regional_elo_player_stats**: UNUSED
- **regional_elo_primary_state_assignments**: UNUSED
- **regional_elo_ratings**: UNUSED
- **regional_elo_regions**: UNUSED
- **regional_elo_state_activity**: UNUSED
- **round_win_rates**: UNUSED
- **seat_position_stats**: UNUSED
- **seat_survival_by_commander**: UNUSED
- **seat_survival_by_round**: UNUSED
- **spice_cards_report**: Used by Backend: win_rate_correlation.py, Frontend: app/trap-spice/page.tsx
- **survival_summary**: UNUSED
- **trap_cards_report**: Used by Backend: win_rate_correlation.py, Frontend: app/trap-spice/page.tsx

## Materialized Views
- **card_frequencies_by_commander**: Used by Frontend: app/trap-spice/page.tsx, Backend: card_frequency.py
- **card_frequencies_global**: Used by Backend: card_frequency.py
- **card_performance_by_commander**: Used by Backend: win_rate_correlation.py, Frontend: lib/commanders/fetchers.ts
- **card_performance_global**: Used by Backend: win_rate_correlation.py
- **commander_monthly_trends**: Used by Frontend: app/commanders/page.tsx, Frontend: app/page.tsx, Frontend: lib/commanders/fetchers.ts
- **commander_seat_stats**: UNUSED
- **commander_weekly_trends**: Used by Frontend: app/commanders/page.tsx, Frontend: app/page.tsx, Frontend: lib/commanders/fetchers.ts
- **for**: UNUSED
- **regional_elo_data_validity**: UNUSED

## RPCs
- **calculate_conversion_score**: UNUSED
- **classify_card_tier**: UNUSED
- **cleanup_stale_elo_jobs**: UNUSED
- **cleanup_stale_ingestion_jobs**: UNUSED
- **compute_game_key**: UNUSED
- **enqueue_elo_refresh**: UNUSED
- **enqueue_ingestion_refresh**: UNUSED
- **get_active_global_elo_player_ids**: UNUSED
- **get_commander_matchups**: Used by Backend: commander_ev_simulations.py, Frontend: lib/commanders/fetchers.ts
- **get_commander_matchups_count**: UNUSED
- **get_commander_round_stats**: UNUSED
- **get_commanders_for_card**: UNUSED
- **get_global_elo_player_meta_snapshot**: UNUSED
- **get_global_elo_snapshot_before**: UNUSED
- **get_global_elo_state_activity_snapshot**: UNUSED
- **get_notable_players_for_commander**: Used by Frontend: lib/commanders/fetchers.ts
- **get_regional_elo_query_stats**: UNUSED
- **is_service_role**: UNUSED
- **parse_decklist**: UNUSED
- **refresh_card_frequencies**: UNUSED
- **refresh_card_performance**: UNUSED
- **refresh_commander_trends**: UNUSED
- **refresh_regional_elo_data_validity**: UNUSED
- **set_canonical_game_key**: UNUSED
- **trigger_elo_refresh_via_edge**: UNUSED
- **trigger_ingestion_refresh_via_edge**: UNUSED
- **trigger_topdeck_elo_import_via_edge**: UNUSED
- **update_updated_at**: UNUSED
