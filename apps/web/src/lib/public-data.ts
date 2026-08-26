import "server-only";

import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";
import { assignEventTier, type EventTier, type TournamentSummary } from "@/lib/tournaments";

export type PublicSearchResult =
  | { kind: "commander"; id: string; name: string; color_identity: string[] | null }
  | { kind: "player"; topdeck_id: string; name: string }
  | { kind: "tournament"; slug: string; name: string; date: string | null; players: number | null };

type TournamentRow = {
  id: string;
  topdeck_tid: string | null;
  name: string | null;
  start_date: string | null;
  player_count: number | null;
  tier: EventTier | null;
};

type TopCutRow = {
  tournament_id: string;
  final_standing: number;
  players: { name: string | null } | Array<{ name: string | null }> | null;
  commanders:
    | { name: string | null; color_identity: string[] | null }
    | Array<{ name: string | null; color_identity: string[] | null }>
    | null;
};

function firstRelation<T>(value: T | T[] | null | undefined): T | null {
  if (!value) return null;
  return Array.isArray(value) ? value[0] ?? null : value;
}

async function searchPublicData(query: string): Promise<PublicSearchResult[]> {
  const pattern = `%${query}%`;
  const [commanderRes, playerRes, tournamentRes] = await Promise.all([
    supabase
      .from("commander_stats")
      .select("commander_id, commander_name, color_identity")
      .ilike("commander_name", pattern)
      .not("commander_name", "ilike", "unknown commander")
      .order("total_entries", { ascending: false })
      .limit(5),
    supabase
      .from("players")
      .select("topdeck_id, name")
      .ilike("name", pattern)
      .not("topdeck_id", "is", null)
      .limit(5),
    supabase
      .from("tournaments")
      .select("topdeck_tid, name, start_date, player_count, tournament_entries!inner(final_standing)")
      .ilike("name", pattern)
      .not("topdeck_tid", "is", null)
      .not("tournament_entries.final_standing", "is", null)
      .lte("start_date", new Date().toISOString())
      .order("start_date", { ascending: false })
      .limit(5)
      .limit(1, { referencedTable: "tournament_entries" }),
  ]);

  return [
    ...(commanderRes.data ?? []).map((row) => ({
      kind: "commander" as const,
      id: row.commander_id as string,
      name: row.commander_name as string,
      color_identity: (row.color_identity as string[] | null) ?? null,
    })),
    ...(playerRes.data ?? []).map((row) => ({
      kind: "player" as const,
      topdeck_id: row.topdeck_id as string,
      name: row.name as string,
    })),
    ...(tournamentRes.data ?? []).map((row) => ({
      kind: "tournament" as const,
      slug: row.topdeck_tid as string,
      name: (row.name as string | null) ?? "",
      date: (row.start_date as string | null) ?? null,
      players: (row.player_count as number | null) ?? null,
    })),
  ];
}

export const getCachedPublicSearch = unstable_cache(
  async (query: string) => searchPublicData(query),
  ["public-search-v1"],
  { revalidate: 300 }
);

async function fetchTournamentSummaries(): Promise<TournamentSummary[]> {
  const { data, error } = await supabase
    .from("tournaments")
    .select("id, topdeck_tid, name, start_date, player_count, tier")
    .not("topdeck_tid", "is", null)
    .gte("player_count", 16)
    .lte("start_date", new Date().toISOString())
    .order("start_date", { ascending: false })
    .limit(100);
  if (error || !data?.length) return [];

  const rows = data as TournamentRow[];
  const { data: topRows } = await supabase
    .from("tournament_entries")
    .select("tournament_id, final_standing, players(name), commanders(name, color_identity)")
    .in("tournament_id", rows.map((row) => row.id))
    .lte("final_standing", 4)
    .order("final_standing", { ascending: true });

  const topCutByTournamentId = new Map<string, NonNullable<TournamentSummary["topCut"]>>();
  for (const row of ((topRows ?? []) as unknown as TopCutRow[])) {
    const entries = topCutByTournamentId.get(row.tournament_id) ?? [];
    entries.push({
      standing: row.final_standing,
      name: firstRelation(row.players)?.name ?? "Unknown",
      commander: firstRelation(row.commanders)?.name ?? "Unknown Commander",
      colors: firstRelation(row.commanders)?.color_identity ?? [],
    });
    topCutByTournamentId.set(row.tournament_id, entries);
  }

  return rows
    .filter((row) => row.topdeck_tid && row.name && row.start_date && row.player_count)
    .map((row) => {
      const topCut = topCutByTournamentId.get(row.id) ?? [];
      return {
        name: row.name!.trim(),
        date: row.start_date!.slice(0, 10),
        players: row.player_count!,
        winner: topCut.find((entry) => entry.standing === 1)?.name ?? "—",
        topCut,
        slug: row.topdeck_tid!,
        topdeckTid: row.topdeck_tid!,
        tier: row.tier ?? assignEventTier(row.player_count!),
        hasDetail: true,
      };
    });
}

export const getCachedTournamentSummaries = unstable_cache(
  fetchTournamentSummaries,
  ["public-tournament-summaries-v1"],
  { revalidate: 3600 }
);

export const getCachedTrapSpiceData = unstable_cache(
  async () => {
    const [commanderRes, trapRes, spiceRes] = await Promise.all([
      supabase
        .from("commander_stats")
        .select("commander_id, commander_name, total_entries")
        .gt("total_entries", 10)
        .not("commander_name", "ilike", "unknown commander")
        .order("total_entries", { ascending: false }),
      supabase.from("trap_cards_report").select("*").order("trap_score", { ascending: false }).limit(100),
      supabase.from("spice_cards_report").select("*").order("win_rate_delta", { ascending: false }).limit(100),
    ]);

    for (const result of [commanderRes, trapRes, spiceRes]) {
      if (result.error) throw result.error;
    }

    const cardNames = [...(trapRes.data ?? []), ...(spiceRes.data ?? [])].map((row) => row.card_name);
    const usageRes = cardNames.length
      ? await supabase
          .from("card_frequencies_by_commander")
          .select("card_name, commander_id, commander, deck_count, inclusion_rate")
          .in("card_name", cardNames)
          .order("deck_count", { ascending: false })
      : { data: [], error: null };
    if (usageRes.error) throw usageRes.error;
    const usageRows = usageRes.data;

    const usage = new Map<string, unknown[]>();
    for (const row of usageRows ?? []) {
      const values = usage.get(row.card_name) ?? [];
      if (values.length < 10) values.push(row);
      usage.set(row.card_name, values);
    }
    const attachUsage = (rows: Record<string, unknown>[]) =>
      rows.map((row) => ({ ...row, top_commanders: usage.get(String(row.card_name)) ?? [] }));

    return {
      commanders: commanderRes.data ?? [],
      trapCards: attachUsage((trapRes.data ?? []) as Record<string, unknown>[]),
      spiceCards: attachUsage((spiceRes.data ?? []) as Record<string, unknown>[]),
    };
  },
  ["public-trap-spice-v1"],
  { revalidate: 86400 }
);
