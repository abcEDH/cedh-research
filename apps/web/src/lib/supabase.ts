import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Type definitions for the materialized views
export interface CommanderStat {
  commander_id: string;
  commander_name: string;
  archetype?: string;
  color_identity: string[];
  total_entries: number;
  tournaments_played: number;
  avg_win_rate: number;
  conversion_rate_top_16: number;
  conversion_rate_top_cut: number;
}

export interface SeatPositionStat {
  seat_position: number;
  total_games: number;
  wins: number;
  losses: number;
  draws: number;
  win_rate: number;
}

export interface GlobalCardFrequency {
  card_name: string;
  deck_count: number;
  total_decks: number;
  inclusion_rate: number;
  commander_count: number;
  tier: 'core' | 'essential' | 'common' | 'flex' | 'spice';
}

export interface TrapCard {
  card_name: string;
  inclusion_rate: number;
  win_rate: number;
  win_rate_delta: number;
  trap_score: number;
}

export interface SpiceCard {
  card_name: string;
  inclusion_rate: number;
  win_rate: number;
  win_rate_delta: number;
  commander_count: number;
}

export interface CommanderHeadToHead {
  commander_id: string;
  commander_name: string;
  opponent_commander_id: string;
  opponent_commander_name: string;
  games_played: number;
  wins: number;
  win_rate: number;
}
