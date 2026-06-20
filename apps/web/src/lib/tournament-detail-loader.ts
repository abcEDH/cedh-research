import "server-only";

import { supabase } from "@/lib/supabase";
import {
  curatedTournamentDetails,
  getTournamentSummary,
  tournamentSummaries,
  type CommanderDistEntry,
  type Standing,
  type TournamentDetail,
} from "@/lib/tournaments";

type TournamentRow = {
  id: string;
  topdeck_tid: string | null;
  name: string | null;
  start_date: string | null;
  player_count: number | null;
  swiss_rounds: number | null;
  top_cut: number | null;
};

type EntryRow = {
  final_standing: number | null;
  wins: number | null;
  losses: number | null;
  draws: number | null;
  decklist_url: string | null;
  made_top_cut: boolean | null;
  made_top_16: boolean | null;
  players: {
    name: string | null;
    topdeck_id: string | null;
    topdeck_handle: string | null;
  } | Array<{
    name: string | null;
    topdeck_id: string | null;
    topdeck_handle: string | null;
  }> | null;
  commanders: {
    name: string | null;
    color_identity: string[] | null;
  } | Array<{
    name: string | null;
    color_identity: string[] | null;
  }> | null;
};

export function staticTournamentParams() {
  return tournamentSummaries.map((event) => ({ slug: event.slug }));
}

export async function loadTournamentDetail(slug: string): Promise<TournamentDetail | null> {
  const summary = getTournamentSummary(slug);

  const loaded = await loadSupabaseTournamentDetail(slug, summary).catch((error) => {
    console.error(`Tournament detail load failed for ${slug}:`, error);
    return null;
  });

  const curated = curatedTournamentDetails[slug];
  if (!loaded) return curated ?? null;
  if (!curated) return loaded;

  return {
    ...curated,
    name: loaded.name,
    date: loaded.date,
    players: loaded.players,
    rounds: loaded.rounds,
    cutSize: loaded.cutSize,
    winner: loaded.winner,
    winnerCmd: loaded.winnerCmd,
    winnerColors: loaded.winnerColors,
    source: loaded.source,
    standings: loaded.standings,
    cmdDist: loaded.cmdDist,
  };
}

async function loadSupabaseTournamentDetail(
  slug: string,
  summary: ReturnType<typeof getTournamentSummary>
): Promise<TournamentDetail | null> {
  const { data: tournament, error: tournamentError } = await supabase
    .from("tournaments")
    .select("id, topdeck_tid, name, start_date, player_count, swiss_rounds, top_cut")
    .eq("topdeck_tid", summary?.topdeckTid ?? slug)
    .maybeSingle();

  if (tournamentError) throw tournamentError;
  if (!tournament) return null;

  const row = tournament as TournamentRow;
  const { data: entryRows, error: entriesError } = await supabase
    .from("tournament_entries")
    .select(
      "final_standing, wins, losses, draws, decklist_url, made_top_cut, made_top_16, players(name, topdeck_id, topdeck_handle), commanders(name, color_identity)"
    )
    .eq("tournament_id", row.id)
    .order("final_standing", { ascending: true, nullsFirst: false })
    .limit(600);

  if (entriesError) throw entriesError;

  const topdeckTid = row.topdeck_tid ?? summary?.topdeckTid ?? slug;
  const standings = ((entryRows ?? []) as unknown as EntryRow[])
    .filter((entry) => entry.final_standing !== null)
    .map((entry, index) => toStanding(entry, topdeckTid, index));

  if (standings.length === 0) return null;

  const winner = standings[0];
  const players = row.player_count ?? summary?.players ?? standings.length;
  const rounds = row.swiss_rounds && row.swiss_rounds > 0 ? row.swiss_rounds : inferRounds(players);
  const cutSize = row.top_cut && row.top_cut > 0 ? row.top_cut : inferCutSize(players);

  return {
    name: (row.name ?? summary?.name ?? topdeckTid).trim(),
    date: (row.start_date ?? summary?.date ?? "").slice(0, 10),
    players,
    winner: winner.player,
    slug: summary?.slug ?? topdeckTid,
    topdeckTid,
    rounds,
    cutSize,
    winnerCmd: winner.commander,
    winnerColors: winner.colors,
    source: `https://topdeck.gg/bracket/${topdeckTid}`,
    bracketAvailable: false,
    standings,
    narratives: buildLoadedNarratives({
      players,
      rounds,
      cutSize,
      winner: winner.player,
      winnerCmd: winner.commander,
      topRecord: `${winner.wins}-${winner.losses}-${winner.draws}`,
    }),
    cmdDist: distributionFromStandings(standings, cutSize),
    bracket: {
      swiss: { topSeed: winner.player, topRecord: `${winner.wins}-${winner.losses}-${winner.draws}` },
      t40: [],
      t16: [],
      t4: { players: [] },
    },
  };
}

function toStanding(entry: EntryRow, topdeckTid: string, index: number): Standing {
  const rank = entry.final_standing ?? index + 1;
  const player = firstRelation(entry.players);
  const commander = firstRelation(entry.commanders);
  const topdeckId = player?.topdeck_id;
  const decklistUrl = entry.decklist_url ?? (topdeckId ? `https://topdeck.gg/deck/${topdeckTid}/${topdeckId}` : null);
  const colors = (commander?.color_identity ?? []).join("");

  return {
    rank,
    player: player?.name ?? player?.topdeck_handle ?? "Unknown Player",
    team: "",
    commander: commander?.name ?? "Unknown Commander",
    colors,
    wins: entry.wins ?? 0,
    losses: entry.losses ?? 0,
    draws: entry.draws ?? 0,
    cut: cutLabel(rank, Boolean(entry.made_top_cut), Boolean(entry.made_top_16)),
    decklistUrl,
    topdeckId,
  };
}

function firstRelation<T>(value: T | T[] | null | undefined): T | null {
  if (!value) return null;
  return Array.isArray(value) ? value[0] ?? null : value;
}

function cutLabel(rank: number, madeTopCut: boolean, madeTop16: boolean): Standing["cut"] {
  if (rank === 1) return "Champion";
  if (rank <= 4) return "Top 4";
  if (madeTop16 || rank <= 16) return "Top 16";
  if (madeTopCut && rank <= 32) return "Top 32";
  if (madeTopCut && rank <= 40) return "Top 40";
  return "—";
}

function inferRounds(players: number) {
  if (players >= 180) return 8;
  if (players >= 100) return 7;
  return 6;
}

function inferCutSize(players: number): 16 | 32 | 40 {
  if (players >= 200) return 40;
  if (players >= 100) return 32;
  return 16;
}

function distributionFromStandings(standings: Standing[], cutSize: number): CommanderDistEntry[] {
  const cutRows = standings.filter((row) => row.cut !== "—").slice(0, cutSize);
  const rows = cutRows.length > 0 ? cutRows : standings.slice(0, cutSize);
  const counts = new Map<string, { colors: string; count: number }>();

  for (const row of rows) {
    const current = counts.get(row.commander) ?? { colors: row.colors, count: 0 };
    current.count += 1;
    counts.set(row.commander, current);
  }

  return [...counts.entries()]
    .map(([name, value]) => ({
      name,
      colors: value.colors,
      count: value.count,
      pct: Number(((value.count / rows.length) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
}

function buildLoadedNarratives(event: {
  players: number;
  rounds: number;
  cutSize: number;
  winner: string;
  winnerCmd: string;
  topRecord: string;
}): TournamentDetail["narratives"] {
  return [
    {
      stageNum: "01",
      stageLabel: "Swiss Rounds",
      roundRange: `Rounds 1-${event.rounds} · ${event.players} players`,
      isCut: false,
      isChamp: false,
      stat: event.topRecord,
      statLabel: "Winner Record",
      narrative: `${event.players} players are loaded from tournament entry records. Standings include all captured players with records and decklist links when TopDeck player IDs are available.`,
      spotlight: `${event.winner} is recorded as the event winner on ${event.winnerCmd}.`,
      spotlightIcon: "★",
    },
    {
      stageNum: "02",
      stageLabel: `Top ${event.cutSize} Cut`,
      roundRange: `${event.players} → ${event.cutSize} players`,
      isCut: true,
      isChamp: false,
      stat: `${event.cutSize}`,
      statLabel: "Cut Size",
      narrative: "Top-cut labels are loaded from tournament entry flags when available. Non-cut players remain visible in the full standings table.",
      spotlight: "Pod-by-pod bracket reconstruction is only shown when reliable bracket data is available.",
      spotlightIcon: "↑",
    },
    {
      stageNum: "03",
      stageLabel: "Champion",
      roundRange: `Final record: ${event.topRecord}`,
      isCut: false,
      isChamp: true,
      stat: "1st",
      statLabel: "Finish",
      narrative: `${event.winner} is the recorded champion. Decklist links open TopDeck deck pages in a new tab.`,
      spotlight: "",
      spotlightIcon: "",
    },
  ];
}
