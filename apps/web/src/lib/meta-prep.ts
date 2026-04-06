import "server-only";
import { supabase } from "@/lib/supabase";

export type CommanderUsageRow = {
  topdeck_id: string | null;
  player_name: string | null;
  commander_name: string | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  start_date: string | null;
  decklist_url: string | null;
  topdeck_decklist_url: string | null;
};

type Relation<T> = T | T[] | null;

type CommanderUsageQueryRow = {
  decklist_url: string | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  players: Relation<{
    topdeck_id: string | null;
    name: string | null;
  }>;
  commanders: Relation<{
    name: string | null;
  }>;
  tournaments: Relation<{
    start_date: string | null;
    topdeck_tid: string | null;
  }>;
};

export type PlayerCommanderProfile = {
  topdeckId: string;
  playerName: string;
  totalEntries: number;
  commanders: Array<{
    commander: string;
    entries: number;
    share: number;
    weightedShare: number;
    predictionShare: number;
    predictionScore: number;
    latestDate: string | null;
    latestDecklistUrl: string | null;
    latestTopdeckDecklistUrl: string | null;
  }>;
};

export type MetaShareRow = {
  commander: string;
  entries: number;
  share: number;
};

export type CommanderDecklistRow = {
  topdeck_id: string | null;
  commander_name: string | null;
  start_date: string | null;
  decklist_url: string | null;
  topdeck_decklist_url: string | null;
};

function isKnownCommander(commanderName: string | null | undefined) {
  const normalized = (commanderName ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

function firstRelation<T>(value: Relation<T>) {
  return Array.isArray(value) ? value[0] ?? null : value;
}

function extractDecklistUrl(value: string | null) {
  if (!value) return null;
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return trimmed.match(/https?:\/\/\S+/i)?.[0] ?? null;
}

function extractCommanderNameFromDecklist(value: string | null) {
  if (!value || !value.includes("~~Commanders~~")) return null;
  const normalized = value.replace(/\\n/g, "\n");
  const [, commanderBlock] = normalized.split("~~Commanders~~");
  const [commanders] = commanderBlock.split(/~~\w+~~|\n\s*\n/);
  const commanderNames = commanders
    .split("\n")
    .map((line) => line.trim().replace(/^\d+x?\s+/i, ""))
    .filter(Boolean);

  return commanderNames.length ? commanderNames.join(" / ") : null;
}

function commanderKey(value: string) {
  return value
    .split("/")
    .map((part) =>
      part
        .toLowerCase()
        .replace(/[’‘]/g, "'")
        .replace(/[^a-z0-9]+/g, " ")
        .trim()
    )
    .filter(Boolean)
    .sort()
    .join(" / ");
}

function decklistProfileKey(topdeckId: string, commanderName: string) {
  return `${topdeckId}:${commanderKey(commanderName)}`;
}

function buildTopdeckDecklistUrl(tournamentSlug: string | null | undefined, topdeckId: string | null | undefined) {
  return tournamentSlug && topdeckId ? `https://topdeck.gg/deck/${tournamentSlug}/${topdeckId}` : null;
}

export async function getCommanderUsageRows(
  topdeckIds: string[],
  lookbackStart: string
): Promise<CommanderUsageRow[]> {
  if (topdeckIds.length === 0) return [];

  const { data, error } = await supabase
    .from("tournament_entries")
    .select(
      "decklist_url, wins, draws, losses, players!inner(topdeck_id, name), commanders!inner(name), tournaments!inner(start_date, topdeck_tid)"
    )
    .in("players.topdeck_id", topdeckIds)
    .gte("tournaments.start_date", lookbackStart)
    .not("commanders.name", "is", null);

  if (error) {
    throw new Error(`Error fetching commander usage: ${error.message}`);
  }

  return ((data ?? []) as CommanderUsageQueryRow[]).map((row) => {
    const player = firstRelation(row.players);
    const commander = firstRelation(row.commanders);
    const tournament = firstRelation(row.tournaments);
    const parsedCommanderName = extractCommanderNameFromDecklist(row.decklist_url);
    const commanderName = isKnownCommander(commander?.name)
      ? commander?.name ?? null
      : parsedCommanderName;
    return {
      topdeck_id: player?.topdeck_id ?? null,
      player_name: player?.name ?? null,
      commander_name: commanderName,
      wins: row.wins,
      draws: row.draws,
      losses: row.losses,
      start_date: tournament?.start_date ?? null,
      decklist_url: extractDecklistUrl(row.decklist_url),
      topdeck_decklist_url: buildTopdeckDecklistUrl(tournament?.topdeck_tid, player?.topdeck_id),
    };
  });
}

export async function getCommanderDecklistRows(topdeckIds: string[]): Promise<CommanderDecklistRow[]> {
  if (topdeckIds.length === 0) return [];

  const { data, error } = await supabase
    .from("tournament_entries")
    .select("decklist_url, players!inner(topdeck_id), commanders!inner(name), tournaments!inner(start_date, topdeck_tid)")
    .in("players.topdeck_id", topdeckIds)
    .not("decklist_url", "is", null);

  if (error) {
    throw new Error(`Error fetching commander decklists: ${error.message}`);
  }

  return ((data ?? []) as CommanderUsageQueryRow[]).map((row) => {
    const player = firstRelation(row.players);
    const commander = firstRelation(row.commanders);
    const tournament = firstRelation(row.tournaments);
    const parsedCommanderName = extractCommanderNameFromDecklist(row.decklist_url);
    const commanderName = isKnownCommander(commander?.name)
      ? commander?.name ?? null
      : parsedCommanderName;

    return {
      topdeck_id: player?.topdeck_id ?? null,
      commander_name: commanderName,
      start_date: tournament?.start_date ?? null,
      decklist_url: extractDecklistUrl(row.decklist_url),
      topdeck_decklist_url: buildTopdeckDecklistUrl(tournament?.topdeck_tid, player?.topdeck_id),
    };
  });
}

export function attachLatestDecklistUrls(
  profiles: { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] },
  decklistRows: CommanderDecklistRow[]
) {
  const latestDecklistByProfile = new Map<
    string,
    {
      startDate: string | null;
      url: string;
      topdeckUrl: string | null;
    }
  >();

  for (const row of decklistRows) {
    const commanderName = row.commander_name;
    if (!row.topdeck_id || !commanderName || !isKnownCommander(commanderName)) continue;
    const url = row.decklist_url || row.topdeck_decklist_url;
    if (!url) continue;
    const key = decklistProfileKey(row.topdeck_id, commanderName);
    const current = latestDecklistByProfile.get(key);
    if (!current || (row.start_date && row.start_date > (current.startDate ?? ""))) {
      latestDecklistByProfile.set(key, {
        startDate: row.start_date,
        url,
        topdeckUrl: row.topdeck_decklist_url,
      });
    }
  }

  return {
    ...profiles,
    players: profiles.players.map((player) => ({
      ...player,
      commanders: player.commanders.map((commander) => ({
        ...commander,
        latestDecklistUrl:
          commander.latestDecklistUrl ||
          latestDecklistByProfile.get(decklistProfileKey(player.topdeckId, commander.commander))
            ?.url ||
          null,
        latestTopdeckDecklistUrl:
          commander.latestTopdeckDecklistUrl ||
          latestDecklistByProfile.get(decklistProfileKey(player.topdeckId, commander.commander))
            ?.topdeckUrl ||
          null,
      })),
    })),
  };
}

export function buildProfiles(
  topdeckIds: string[],
  usageRows: CommanderUsageRow[],
  topN = 3
): { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } {
  const perPlayer = new Map<
    string,
    Map<
      string,
      {
        entries: number;
        weightedPoints: number;
        predictionScore: number;
        latestDate: string | null;
        latestDecklistDate: string | null;
        latestDecklistUrl: string | null;
        latestTopdeckDecklistUrl: string | null;
        playerName: string;
      }
    >
  >();
  const playerNames = new Map<string, string>();
  const commanderTotals = new Map<string, number>();
  const latestTimestamp = usageRows.reduce((max, row) => {
    const timestamp = row.start_date ? new Date(row.start_date).getTime() : 0;
    return Number.isFinite(timestamp) ? Math.max(max, timestamp) : max;
  }, 0);

  usageRows.forEach((row) => {
    if (!row.topdeck_id || !isKnownCommander(row.commander_name)) return;
    const commanderName = row.commander_name as string;
    const playerName = row.player_name ?? "Unknown";
    if (row.player_name) {
      playerNames.set(row.topdeck_id, row.player_name);
    }
    const perCommander = perPlayer.get(row.topdeck_id) ?? new Map();
    const current = perCommander.get(commanderName) ?? {
      entries: 0,
      weightedPoints: 0,
      predictionScore: 0,
      latestDate: null,
      latestDecklistDate: null,
      latestDecklistUrl: null,
      latestTopdeckDecklistUrl: null,
      playerName,
    };
    const wins = row.wins ?? 0;
    const draws = row.draws ?? 0;
    const losses = row.losses ?? 0;
    const games = wins + draws + losses;
    const points = wins + draws * 0.25;
    const eventTimestamp = row.start_date ? new Date(row.start_date).getTime() : 0;
    const recencyWeight =
      latestTimestamp > 0 && eventTimestamp > 0
        ? Math.max(0.35, 1 - (latestTimestamp - eventTimestamp) / (1000 * 60 * 60 * 24 * 30 * 18))
        : 0.5;
    const efficiencyBoost = games > 0 ? 1 + points / games : 1;

    current.entries += 1;
    current.weightedPoints += points;
    current.predictionScore += recencyWeight * efficiencyBoost;
    if (!current.latestDate || (row.start_date && row.start_date > current.latestDate)) {
      current.latestDate = row.start_date;
      if (row.topdeck_decklist_url) {
        current.latestTopdeckDecklistUrl = row.topdeck_decklist_url;
      }
    }
    if (
      row.decklist_url &&
      (!current.latestDecklistDate ||
        (row.start_date && row.start_date >= current.latestDecklistDate))
    ) {
      current.latestDecklistDate = row.start_date;
      current.latestDecklistUrl = row.decklist_url;
      current.latestTopdeckDecklistUrl = row.topdeck_decklist_url;
    }
    perCommander.set(commanderName, current);
    perPlayer.set(row.topdeck_id, perCommander);

    commanderTotals.set(commanderName, (commanderTotals.get(commanderName) ?? 0) + 1);
  });

  const totalEntries = Array.from(commanderTotals.values()).reduce((a, b) => a + b, 0);

  const players: PlayerCommanderProfile[] = topdeckIds.map((topdeckId) => {
    const perCommander = perPlayer.get(topdeckId) ?? new Map();
    const rows = Array.from(perCommander.entries()).map(([commander, values]) => ({
      commander,
      entries: values.entries,
      weightedPoints: values.weightedPoints,
      predictionScore: values.predictionScore,
      latestDate: values.latestDate,
      latestDecklistUrl: values.latestDecklistUrl,
      latestTopdeckDecklistUrl: values.latestTopdeckDecklistUrl,
      playerName: values.playerName,
    }));
    const total = rows.reduce((sum, row) => sum + row.entries, 0);
    const totalWeighted = rows.reduce((sum, row) => sum + row.weightedPoints, 0);
    const totalPrediction = rows.reduce((sum, row) => sum + row.predictionScore, 0);
    const sorted = rows.sort((a, b) => {
      if (b.predictionScore !== a.predictionScore) return b.predictionScore - a.predictionScore;
      if (b.entries !== a.entries) return b.entries - a.entries;
      return b.weightedPoints - a.weightedPoints;
    });
    const commanders = sorted.slice(0, topN).map((row) => ({
      commander: row.commander,
      entries: row.entries,
      share: total ? row.entries / total : 0,
      weightedShare: totalWeighted ? row.weightedPoints / totalWeighted : total ? row.entries / total : 0,
      predictionShare: totalPrediction ? row.predictionScore / totalPrediction : total ? row.entries / total : 0,
      predictionScore: row.predictionScore,
      latestDate: row.latestDate,
      latestDecklistUrl: row.latestDecklistUrl,
      latestTopdeckDecklistUrl: row.latestTopdeckDecklistUrl,
    }));

    return {
      topdeckId,
      playerName: playerNames.get(topdeckId) || "Unknown",
      totalEntries: total,
      commanders,
    };
  });

  const metaShare: MetaShareRow[] = Array.from(commanderTotals.entries())
    .map(([commander, entries]) => ({
      commander,
      entries,
      share: totalEntries ? entries / totalEntries : 0,
    }))
    .sort((a, b) => b.entries - a.entries)
    .slice(0, 15);

  return { players, metaShare };
}

export function lookbackStartDate(months: number) {
  const start = new Date();
  start.setMonth(start.getMonth() - months);
  return start.toISOString().slice(0, 10);
}
