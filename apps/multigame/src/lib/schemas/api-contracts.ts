/**
 * API contract schemas for the multigame app.
 *
 * Zod schemas describing the rows we read from Supabase. Fetchers validate
 * responses against these so backend contract drift fails loudly instead of
 * rendering garbage.
 */

import { z } from "zod";

// ============================================
// deck_identity_stats read model
// ============================================
export const DeckIdentityStatRowSchema = z.object({
  game: z.string(),
  format: z.string().nullable(),
  identity_id: z.string(),
  name: z.string(),
  identity_kind: z.string(),
  entries: z.number(),
  tournaments_played: z.number(),
  wins: z.number(),
  losses: z.number(),
  draws: z.number(),
  top_cut_count: z.number(),
  avg_win_rate: z.number().nullable(),
});

export type DeckIdentityStatRow = z.infer<typeof DeckIdentityStatRowSchema>;

// ============================================
// tournaments table
// ============================================
export const TournamentRowSchema = z.object({
  id: z.string(),
  topdeck_tid: z.string(),
  name: z.string(),
  start_date: z.string().nullable(),
  game: z.string(),
  format: z.string(),
  player_count: z.number(),
  swiss_rounds: z.number().nullable(),
  top_cut: z.number().nullable(),
  // Not a physical column today; tolerated when a read model adds it.
  tier: z.string().nullable().optional(),
});

export type TournamentRow = z.infer<typeof TournamentRowSchema>;

// ============================================
// tournament_entries (+ joined commanders.name)
// ============================================
export const TournamentEntryRowSchema = z.object({
  id: z.string(),
  final_standing: z.number().nullable(),
  points: z.number().nullable(),
  wins: z.number().nullable(),
  losses: z.number().nullable(),
  draws: z.number().nullable(),
  win_rate: z.number().nullable(),
  decklist_obj: z.unknown().nullable(),
  commanders: z.object({ name: z.string() }).nullable(),
});

export type TournamentEntryRow = z.infer<typeof TournamentEntryRowSchema>;

// ============================================
// TopDeck deckObj payload (tournament_entries.decklist_obj)
// {Commanders|Mainboard|Sideboard: {<cardName>: {id, count}}}
// ============================================
export const DecklistCardSchema = z.object({
  id: z.string().optional(),
  count: z.number(),
});

export const DecklistObjSchema = z.record(z.string(), z.record(z.string(), DecklistCardSchema));

export type DecklistObj = z.infer<typeof DecklistObjSchema>;
