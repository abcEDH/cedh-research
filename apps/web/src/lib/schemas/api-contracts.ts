/**
 * API Contract Schemas
 *
 * These Zod schemas define the expected shape of data from Supabase RPC functions.
 * When the backend changes its response format, these schemas will fail validation,
 * catching the mismatch before it reaches production.
 *
 * Usage:
 * - Import schemas to validate API responses at runtime
 * - Run contract tests to verify backend compatibility
 * - Update schemas when intentionally changing backend contracts
 */

import { z } from "zod";

// ============================================
// Commander Matchups RPC: get_commander_matchups
// ============================================
export const CommanderMatchupSchema = z.object({
  opponent_commander_id: z.string().uuid(),
  opponent_commander_name: z.string(),
  games_played: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  losses: z.number().int().nonnegative(),
  draws: z.number().int().nonnegative(),
  win_rate: z.number().min(0).max(1),
  loss_rate: z.number().min(0).max(1),
  draw_rate: z.number().min(0).max(1),
  expected_win_rate: z.number().min(0).max(1),
  win_rate_vs_expected: z.number(),
  is_statistically_significant: z.boolean(),
  confidence_level: z.enum(["high", "medium", "low", "very_low"]),
});

export const CommanderMatchupsResponseSchema = z.array(CommanderMatchupSchema);

export type CommanderMatchup = z.infer<typeof CommanderMatchupSchema>;

// ============================================
// Notable Players RPC: get_notable_players_for_commander
// ============================================
export const NotablePlayerSchema = z.object({
  player_name: z.string(),
  topdeck_id: z.string().nullable(),
  entries: z.number().int().positive(),
  total_wins: z.number().int().nonnegative(),
  total_games: z.number().int().nonnegative(),
  win_rate: z.string().nullable(),
  top_16_count: z.number().int().nonnegative(),
});

export const NotablePlayersResponseSchema = z.array(NotablePlayerSchema);

export type NotablePlayer = z.infer<typeof NotablePlayerSchema>;

// ============================================
// Survival Curve RPC: get_survival_curve
// ============================================
export const SurvivalPointSchema = z.object({
  round_number: z.number().int().positive(),
  players_at_risk: z.number().int().nonnegative(),
  players_survived: z.number().int().nonnegative(),
  survival_rate: z.union([z.number(), z.string()]).transform((v) =>
    typeof v === "string" ? parseFloat(v) : v
  ),
  cumulative_survival: z.union([z.number(), z.string()]).transform((v) =>
    typeof v === "string" ? parseFloat(v) : v
  ),
});

export const SurvivalCurveResponseSchema = z.array(SurvivalPointSchema);

export type SurvivalPoint = z.infer<typeof SurvivalPointSchema>;

// ============================================
// Survival Curves by Seat View: survival_curves_by_seat
// ============================================
export const SeatSurvivalPointSchema = z.object({
  seat_position: z.number().int().min(0).max(3),
  round_number: z.number().int().positive(),
  players_at_risk: z.number().int().nonnegative(),
  players_survived: z.number().int().nonnegative(),
  survival_rate: z.union([z.number(), z.string()]).transform((v) =>
    typeof v === "string" ? parseFloat(v) : v
  ),
  cumulative_survival: z.union([z.number(), z.string()]).transform((v) =>
    typeof v === "string" ? parseFloat(v) : v
  ),
});

export const SeatSurvivalResponseSchema = z.array(SeatSurvivalPointSchema);

export type SeatSurvivalPoint = z.infer<typeof SeatSurvivalPointSchema>;

// ============================================
// Commander Stats View: commander_stats
// ============================================
export const CommanderStatsSchema = z.object({
  commander_id: z.string().uuid(),
  commander_name: z.string(),
  archetype: z.string().nullable(),
  color_identity: z.array(z.string()).nullable(),
  total_entries: z.number().int().nonnegative(),
  tournaments_played: z.number().int().nonnegative(),
  total_wins: z.number().int().nonnegative(),
  total_losses: z.number().int().nonnegative(),
  total_draws: z.number().int().nonnegative(),
  avg_win_rate: z.string(),
  top_16_count: z.number().int().nonnegative(),
  conversion_rate_top_16: z.string(),
  top_cut_count: z.number().int().nonnegative(),
  conversion_rate_top_cut: z.string(),
});

export type CommanderStats = z.infer<typeof CommanderStatsSchema>;

// ============================================
// Card Frequencies Global View: card_frequencies_global
// ============================================
export const GlobalCardFrequencySchema = z.object({
  card_name: z.string(),
  deck_count: z.number().int().nonnegative(),
  total_decks: z.number().int().positive(),
  inclusion_rate: z.string(),
  commander_count: z.number().int().nonnegative(),
  tier: z.string(),
});

export type GlobalCardFrequency = z.infer<typeof GlobalCardFrequencySchema>;

// ============================================
// Trap Cards Report View: trap_cards_report
// ============================================
export const TrapCardSchema = z.object({
  card_name: z.string(),
  deck_count: z.number().int().nonnegative(),
  inclusion_rate: z.string(),
  avg_win_rate: z.string(),
  baseline_win_rate: z.string(),
  win_rate_delta: z.string(),
  top_16_rate: z.string(),
  commander_count: z.number().int().nonnegative(),
  trap_score: z.string(),
});

export type TrapCard = z.infer<typeof TrapCardSchema>;

// ============================================
// Spice Cards Report View: spice_cards_report
// ============================================
export const SpiceCardSchema = z.object({
  card_name: z.string(),
  deck_count: z.number().int().nonnegative(),
  inclusion_rate: z.string(),
  avg_win_rate: z.string(),
  baseline_win_rate: z.string(),
  win_rate_delta: z.string(),
  top_16_rate: z.string(),
  commander_count: z.number().int().nonnegative(),
});

export type SpiceCard = z.infer<typeof SpiceCardSchema>;

// ============================================
// Validation Helper
// ============================================

/**
 * Validates data against a schema and returns typed result.
 * Throws ZodError with detailed messages if validation fails.
 */
export function validateResponse<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: string
): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.error(`[Contract Violation] ${context}:`, result.error.format());
    throw new Error(
      `API contract violation in ${context}: ${result.error.message}`
    );
  }
  return result.data;
}

/**
 * Safe validation that returns null instead of throwing.
 * Useful for graceful degradation.
 */
export function safeValidateResponse<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: string
): T | null {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.error(`[Contract Warning] ${context}:`, result.error.format());
    return null;
  }
  return result.data;
}
