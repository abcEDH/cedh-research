import "server-only";

import { supabase } from "@/lib/supabase";
import {
  TournamentEntryRowSchema,
  TournamentRowSchema,
  type TournamentEntryRow,
  type TournamentRow,
} from "@/lib/schemas/api-contracts";
import { z } from "zod";

export type { TournamentRow, TournamentEntryRow };

export interface TournamentDetail {
  tournament: TournamentRow;
  entries: TournamentEntryRow[];
}

const TOURNAMENT_COLUMNS =
  "id, topdeck_tid, name, start_date, game, format, player_count, swiss_rounds, top_cut";

/**
 * List tournaments for one game (optionally pinned to a format), newest first.
 * Returns [] on query or validation failure (placeholder Supabase env).
 */
export async function fetchTournaments({
  game,
  format,
  limit = 100,
}: {
  game: string;
  format: string | null;
  limit?: number;
}): Promise<TournamentRow[]> {
  try {
    let query = supabase.from("tournaments").select(TOURNAMENT_COLUMNS).eq("game", game);
    if (format !== null) {
      query = query.eq("format", format);
    }
    const { data, error } = await query
      .order("start_date", { ascending: false })
      .limit(limit);
    if (error || !data) {
      return [];
    }
    return z.array(TournamentRowSchema).parse(data);
  } catch {
    return [];
  }
}

/**
 * One tournament (looked up by TopDeck tid) plus its standings with the
 * joined deck identity name. Returns null when not found or on failure.
 */
export async function fetchTournamentDetail(tid: string): Promise<TournamentDetail | null> {
  try {
    const { data: tournamentData, error: tournamentError } = await supabase
      .from("tournaments")
      .select(TOURNAMENT_COLUMNS)
      .eq("topdeck_tid", tid)
      .maybeSingle();
    if (tournamentError || !tournamentData) {
      return null;
    }
    const tournament = TournamentRowSchema.parse(tournamentData);

    const { data: entriesData, error: entriesError } = await supabase
      .from("tournament_entries")
      .select(
        "id, final_standing, points, wins, losses, draws, win_rate, decklist_obj, commanders(name)"
      )
      .eq("tournament_id", tournament.id)
      .order("final_standing", { ascending: true, nullsFirst: false });
    if (entriesError || !entriesData) {
      return { tournament, entries: [] };
    }
    return { tournament, entries: z.array(TournamentEntryRowSchema).parse(entriesData) };
  } catch {
    return null;
  }
}
