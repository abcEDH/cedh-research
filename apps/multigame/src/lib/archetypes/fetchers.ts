import "server-only";

import { supabase } from "@/lib/supabase";
import {
  DeckIdentityStatRowSchema,
  type DeckIdentityStatRow,
} from "@/lib/schemas/api-contracts";
import { z } from "zod";

export type { DeckIdentityStatRow };

/**
 * Fetch deck identity stats for one game, optionally pinned to a format.
 * `format: null` means the game has no format split — query game-wide.
 *
 * Returns [] on query or validation failure so pages render an empty state
 * (placeholder Supabase env must not break `next build`).
 */
export async function fetchDeckIdentityStats({
  game,
  format,
}: {
  game: string;
  format: string | null;
}): Promise<DeckIdentityStatRow[]> {
  try {
    let query = supabase.from("deck_identity_stats").select("*").eq("game", game);
    if (format !== null) {
      query = query.eq("format", format);
    }
    const { data, error } = await query.order("entries", { ascending: false }).limit(200);
    if (error || !data) {
      return [];
    }
    return z.array(DeckIdentityStatRowSchema).parse(data);
  } catch {
    return [];
  }
}
