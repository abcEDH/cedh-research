import { supabase } from "@/lib/supabase";

const TOPDECK_ELO_CHUNK_SIZE = 250;
const TOPDECK_ELO_PAGE_SIZE = 1000;

type TopdeckEloRow = {
  topdeck_id: string | null;
  elo: number | null;
};

function chunkArray<T>(values: T[], chunkSize = TOPDECK_ELO_CHUNK_SIZE) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += chunkSize) {
    chunks.push(values.slice(index, index + chunkSize));
  }
  return chunks;
}

export async function fetchTopdeckEloMap(topdeckIds: string[]) {
  const eloByTopdeckId = new Map<string, number>();
  const uniqueTopdeckIds = Array.from(new Set(topdeckIds.filter(Boolean)));
  for (const topdeckIdChunk of chunkArray(uniqueTopdeckIds)) {
    const { data, error } = await supabase
      .from("topdeck_player_elos")
      .select("topdeck_id, elo")
      .in("topdeck_id", topdeckIdChunk);

    if (error || !data?.length) continue;
    for (const row of data as TopdeckEloRow[]) {
      if (row.topdeck_id && typeof row.elo === "number") {
        eloByTopdeckId.set(row.topdeck_id, row.elo);
      }
    }
  }
  return eloByTopdeckId;
}

export async function fetchAllTopdeckEloMap() {
  const eloByTopdeckId = new Map<string, number>();
  for (let offset = 0; ; offset += TOPDECK_ELO_PAGE_SIZE) {
    const { data, error } = await supabase
      .from("topdeck_player_elos")
      .select("topdeck_id, elo")
      .order("topdeck_id", { ascending: true })
      .range(offset, offset + TOPDECK_ELO_PAGE_SIZE - 1);

    if (error || !data?.length) break;
    for (const row of data as TopdeckEloRow[]) {
      if (row.topdeck_id && typeof row.elo === "number") {
        eloByTopdeckId.set(row.topdeck_id, row.elo);
      }
    }
    if (data.length < TOPDECK_ELO_PAGE_SIZE) break;
  }
  return eloByTopdeckId;
}

export async function fetchTopdeckElo(topdeckId: string) {
  const { data, error } = await supabase
    .from("topdeck_player_elos")
    .select("topdeck_id, elo")
    .eq("topdeck_id", topdeckId)
    .maybeSingle();

  if (error) return null;
  const row = data as TopdeckEloRow | null;
  return typeof row?.elo === "number" ? row.elo : null;
}