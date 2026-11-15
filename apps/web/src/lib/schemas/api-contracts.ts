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
// Commander Stats View: commander_stats
// ============================================
export const CommanderStatsSchema = z.object({
  commander_id: z.string().uuid(),
  commander_name: z.string(),
  archetype: z.string().nullable(),
  color_identity: z.array(z.string()).nullable(),
  // total_entries/tournaments_played/top_16_count/top_cut_count are COUNT()
  // aggregates in the commander_stats view, which return 0 (never NULL) even
  // when a commander has zero tournament_entries rows.
  total_entries: z.number().int().nonnegative(),
  tournaments_played: z.number().int().nonnegative(),
  // total_wins/total_losses/total_draws/avg_win_rate/conversion_rate_top_16/
  // conversion_rate_top_cut are SUM()/AVG() aggregates computed over a LEFT
  // JOIN to tournament_entries. SUM/AVG of an empty group is legitimately
  // NULL in Postgres, which happens for any commander with zero recorded
  // entries — so these fields must be nullable to match real view output.
  total_wins: z.number().int().nonnegative().nullable(),
  total_losses: z.number().int().nonnegative().nullable(),
  total_draws: z.number().int().nonnegative().nullable(),
  avg_win_rate: z.number().nullable(),
  top_16_count: z.number().int().nonnegative(),
  conversion_rate_top_16: z.number().nullable(),
  top_cut_count: z.number().int().nonnegative(),
  conversion_rate_top_cut: z.number().nullable(),
});

export type CommanderStats = z.infer<typeof CommanderStatsSchema>;

// ============================================
// Card Frequencies Global View: card_frequencies_global
// ============================================
export const GlobalCardFrequencySchema = z.object({
  card_name: z.string(),
  deck_count: z.number().int().nonnegative(),
  total_decks: z.number().int().positive(),
  inclusion_rate: z.number(),
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
  inclusion_rate: z.number(),
  avg_win_rate: z.number(),
  baseline_win_rate: z.number(),
  win_rate_delta: z.number(),
  top_16_rate: z.number(),
  commander_count: z.number().int().nonnegative(),
  trap_score: z.number(),
});

export type TrapCard = z.infer<typeof TrapCardSchema>;

// ============================================
// Spice Cards Report View: spice_cards_report
// ============================================
export const SpiceCardSchema = z.object({
  card_name: z.string(),
  deck_count: z.number().int().nonnegative(),
  inclusion_rate: z.number(),
  avg_win_rate: z.number(),
  baseline_win_rate: z.number(),
  win_rate_delta: z.number(),
  top_16_rate: z.number(),
  commander_count: z.number().int().nonnegative(),
});

export type SpiceCard = z.infer<typeof SpiceCardSchema>;

// ============================================
// Winrate Matrix RPC: get_winrate_matrix (#147, #150)
// ============================================
export const WinrateMatrixRowSchema = z.object({
  deck_a_commander_id: z.string().uuid(),
  // NULL marks the mtgdecks-style OVERALL row for deck_a (aggregate across every opponent in
  // the window, not just the top-N opponents used by the pairwise cells).
  deck_b_commander_id: z.string().uuid().nullable(),
  games_played: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  losses: z.number().int().nonnegative(),
  draws: z.number().int().nonnegative(),
  point_winrate: z.number().min(0).max(1),
  // NULL only when games_played is 0, which get_winrate_matrix never returns (empty cells are
  // omitted) -- kept nullable here defensively so a contract change can't silently pass.
  ci_low: z.number().min(0).max(1).nullable(),
  ci_high: z.number().min(0).max(1).nullable(),
});

export const WinrateMatrixSchema = z.array(WinrateMatrixRowSchema);

export type WinrateMatrixRow = z.infer<typeof WinrateMatrixRowSchema>;

// ============================================
// Pod Metrics RPC: get_pod_metrics (#148, #151)
// ============================================
export const PodMetricSchema = z.object({
  commander_id: z.string().uuid(),
  pods_present: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  top_two: z.number().int().nonnegative(),
  threat_score: z.number().min(0).max(1),
  threat_ci_low: z.number().min(0).max(1).nullable(),
  threat_ci_high: z.number().min(0).max(1).nullable(),
  survivability: z.number().min(0).max(1),
  survivability_ci_low: z.number().min(0).max(1).nullable(),
  survivability_ci_high: z.number().min(0).max(1).nullable(),
  is_statistically_significant: z.boolean(),
});

export const PodMetricsResponseSchema = z.array(PodMetricSchema);

export type PodMetric = z.infer<typeof PodMetricSchema>;

// ============================================
// Commander Meta-EV RPC: get_commander_meta_ev (#149, #150, #151)
// ============================================
export const CommanderMetaEvSchema = z.object({
  commander_id: z.string().uuid(),
  meta_ev: z.number().min(0).max(1),
  meta_ev_ci_low: z.number().min(0).max(1).nullable(),
  meta_ev_ci_high: z.number().min(0).max(1).nullable(),
  // Fraction of this commander's pods whose opponent-triple composition cleared the direct-
  // observation floor (min_triple_obs); a real, deck-specific number, not hardcoded to 1.0.
  composition_coverage: z.number().min(0).max(1),
  // This RPC's own EV-eligible (exactly-4-player-pod) sample size -- narrower than
  // get_pod_metrics' pods_present (that RPC counts every non-bye participation regardless of
  // pod size). The Meta EV badge must use this field, not get_pod_metrics' pods_present, or it
  // overstates how sparse the EV estimate actually is.
  pods_present: z.number().int().nonnegative(),
  is_statistically_significant: z.boolean(),
});

export const CommanderMetaEvResponseSchema = z.array(CommanderMetaEvSchema);

export type CommanderMetaEv = z.infer<typeof CommanderMetaEvSchema>;

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
