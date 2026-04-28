import "server-only";
import { supabase } from "@/lib/supabase";
import { isKnownCommanderName } from "@/lib/commander-utils";
import { chunkArray } from "@/lib/array-utils";

const RECENCY_HALF_LIFE_DAYS = 15;
const SUPABASE_PAGE_SIZE = 1000;
const SUPABASE_IN_CHUNK_SIZE = 100;

export type CommanderUsageRow = {
  topdeck_id: string | null;
  player_name: string | null;
  commander_name: string | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  start_date: string | null;
  player_count: number | null;
  decklist_url: string | null;
  topdeck_decklist_url: string | null;
};

type Relation<T> = T | T[] | null;

type CommanderUsageQueryRow = {
  decklist_url?: string | null;
  player_id: string | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  players?: Relation<{
    topdeck_id: string | null;
    name: string | null;
  }>;
  commanders: Relation<{
    name: string | null;
  }>;
  tournaments: Relation<{
    start_date: string | null;
    player_count: number | null;
    topdeck_tid: string | null;
  }>;
};

type PlayerLookupRow = {
  id: string;
  topdeck_id: string | null;
  name: string | null;
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

export const COMMANDER_PRIMARY_LOOKBACK_MONTHS = 6;
export const COMMANDER_FALLBACK_LOOKBACK_MONTHS = 12;
export const MIN_PRIMARY_COMMANDER_ENTRIES = 2;

function firstRelation<T>(value: Relation<T>) {
  return Array.isArray(value) ? value[0] ?? null : value;
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

function calculateRecencyWeight(eventTimestamp: number, referenceTimestamp: number) {
  if (referenceTimestamp <= 0 || eventTimestamp <= 0) return 0.5;

  const ageInDays = Math.max(0, (referenceTimestamp - eventTimestamp) / (1000 * 60 * 60 * 24));
  return 0.5 ** (ageInDays / RECENCY_HALF_LIFE_DAYS);
}

async function getPlayersByTopdeckIds(topdeckIds: string[]) {
  const playersById = new Map<string, PlayerLookupRow>();

  for (const topdeckIdChunk of chunkArray(topdeckIds, SUPABASE_IN_CHUNK_SIZE)) {
    const { data, error } = await supabase
      .from("players")
      .select("id, topdeck_id, name")
      .in("topdeck_id", topdeckIdChunk);

    if (error) {
      throw new Error(`Error fetching players for commander usage: ${error.message}`);
    }

    for (const row of (data ?? []) as PlayerLookupRow[]) {
      playersById.set(row.id, row);
    }
  }

  return playersById;
}

function mapCommanderUsageRow(
  row: CommanderUsageQueryRow,
  playersById: Map<string, PlayerLookupRow>
): CommanderUsageRow {
  const player = row.player_id ? playersById.get(row.player_id) ?? null : firstRelation(row.players ?? null);
  const commander = firstRelation(row.commanders);
  const tournament = firstRelation(row.tournaments);
  const commanderName = isKnownCommanderName(commander?.name) ? commander?.name ?? null : null;

  return {
    topdeck_id: player?.topdeck_id ?? null,
    player_name: player?.name ?? null,
    commander_name: commanderName,
    wins: row.wins,
    draws: row.draws,
    losses: row.losses,
    start_date: tournament?.start_date ?? null,
    player_count: tournament?.player_count ?? null,
    decklist_url: null,
    topdeck_decklist_url: buildTopdeckDecklistUrl(tournament?.topdeck_tid, player?.topdeck_id),
  };
}

export async function getCommanderUsageRows(
  topdeckIds: string[],
  lookbackStart: string,
  lookbackEnd?: string
): Promise<CommanderUsageRow[]> {
  if (topdeckIds.length === 0) return [];

  const playersById = await getPlayersByTopdeckIds(topdeckIds);
  const playerIds = Array.from(playersById.keys());
  const rows: CommanderUsageRow[] = [];

  for (const playerIdChunk of chunkArray(playerIds, SUPABASE_IN_CHUNK_SIZE)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      let query = supabase
        .from("tournament_entries")
        .select("player_id, wins, draws, losses, commanders!inner(name), tournaments!inner(start_date, player_count, topdeck_tid)")
        .in("player_id", playerIdChunk)
        .gte("tournaments.start_date", lookbackStart)
        .not("commanders.name", "is", null)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);
      if (lookbackEnd) {
        query = query.lt("tournaments.start_date", lookbackEnd);
      }

      const { data, error } = await query;

      if (error) {
        throw new Error(`Error fetching commander usage: ${error.message}`);
      }

      rows.push(
        ...((data ?? []) as CommanderUsageQueryRow[]).map((row) => mapCommanderUsageRow(row, playersById))
      );
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  return rows;
}

export async function getCommanderDecklistRows(
  topdeckIds: string[],
  lookbackEnd?: string
): Promise<CommanderDecklistRow[]> {
  if (topdeckIds.length === 0) return [];

  const playersById = await getPlayersByTopdeckIds(topdeckIds);
  const playerIds = Array.from(playersById.keys());
  const rows: CommanderDecklistRow[] = [];

  for (const playerIdChunk of chunkArray(playerIds, SUPABASE_IN_CHUNK_SIZE)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      let query = supabase
        .from("tournament_entries")
        .select("player_id, commanders!inner(name), tournaments!inner(start_date, topdeck_tid)")
        .in("player_id", playerIdChunk)
        .not("commanders.name", "is", null)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);
      if (lookbackEnd) {
        query = query.lt("tournaments.start_date", lookbackEnd);
      }

      const { data, error } = await query;

      if (error) {
        throw new Error(`Error fetching commander decklists: ${error.message}`);
      }

      rows.push(
        ...((data ?? []) as CommanderUsageQueryRow[]).map((row) => {
          const player = row.player_id ? playersById.get(row.player_id) ?? null : firstRelation(row.players ?? null);
          const commander = firstRelation(row.commanders);
          const tournament = firstRelation(row.tournaments);
          const commanderName = isKnownCommanderName(commander?.name) ? commander?.name ?? null : null;

          return {
            topdeck_id: player?.topdeck_id ?? null,
            commander_name: commanderName,
            start_date: tournament?.start_date ?? null,
            decklist_url: null,
            topdeck_decklist_url: buildTopdeckDecklistUrl(tournament?.topdeck_tid, player?.topdeck_id),
          };
        })
      );
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  return rows;
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
    if (!row.topdeck_id || !commanderName || !isKnownCommanderName(commanderName)) continue;
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
  topN = 3,
  referenceDate?: string | null
): { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } {
  const perPlayer = new Map<
    string,
    Map<
      string,
      {
        entries: number;
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
  const fallbackTimestamp = usageRows.reduce((max, row) => {
    const timestamp = row.start_date ? new Date(row.start_date).getTime() : 0;
    return Number.isFinite(timestamp) ? Math.max(max, timestamp) : max;
  }, 0);
  const parsedReferenceTimestamp = referenceDate ? new Date(referenceDate).getTime() : Number.NaN;
  const referenceTimestamp = Number.isFinite(parsedReferenceTimestamp)
    ? parsedReferenceTimestamp
    : fallbackTimestamp;

  usageRows.forEach((row) => {
    if (!row.topdeck_id || !isKnownCommanderName(row.commander_name)) return;
    const commanderName = row.commander_name as string;
    const playerName = row.player_name ?? "Unknown";
    if (row.player_name) {
      playerNames.set(row.topdeck_id, row.player_name);
    }
    const perCommander = perPlayer.get(row.topdeck_id) ?? new Map();
    const current = perCommander.get(commanderName) ?? {
      entries: 0,
      predictionScore: 0,
      latestDate: null,
      latestDecklistDate: null,
      latestDecklistUrl: null,
      latestTopdeckDecklistUrl: null,
      playerName,
    };
    const eventTimestamp = row.start_date ? new Date(row.start_date).getTime() : 0;
    const recencyWeight = calculateRecencyWeight(eventTimestamp, referenceTimestamp);

    current.entries += 1;
    current.predictionScore += recencyWeight;
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
      predictionScore: values.predictionScore,
      latestDate: values.latestDate,
      latestDecklistUrl: values.latestDecklistUrl,
      latestTopdeckDecklistUrl: values.latestTopdeckDecklistUrl,
      playerName: values.playerName,
    }));
    const total = rows.reduce((sum, row) => sum + row.entries, 0);
    const totalPrediction = rows.reduce((sum, row) => sum + row.predictionScore, 0);
    const sorted = rows.sort((a, b) => {
      if (b.predictionScore !== a.predictionScore) return b.predictionScore - a.predictionScore;
      if (b.entries !== a.entries) return b.entries - a.entries;
      if ((b.latestDate ?? "") !== (a.latestDate ?? "")) {
        return (b.latestDate ?? "").localeCompare(a.latestDate ?? "");
      }
      return a.commander.localeCompare(b.commander);
    });
    const commanders = sorted.slice(0, topN).map((row) => ({
      commander: row.commander,
      entries: row.entries,
      share: total ? row.entries / total : 0,
      weightedShare: totalPrediction ? row.predictionScore / totalPrediction : total ? row.entries / total : 0,
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

export function lookbackStartDate(months: number, referenceDate: Date = new Date()) {
  const start = new Date(referenceDate);
  start.setMonth(start.getMonth() - months);
  return start.toISOString().slice(0, 10);
}

function latestUsageRow(rows: CommanderUsageRow[]) {
  return [...rows].sort((a, b) => (b.start_date ?? "").localeCompare(a.start_date ?? ""))[0] ?? null;
}

export function selectCommanderForecastRows(
  topdeckIds: string[],
  usageRows: CommanderUsageRow[],
  referenceDate: Date = new Date()
) {
  const primaryLookbackStart = lookbackStartDate(COMMANDER_PRIMARY_LOOKBACK_MONTHS, referenceDate);
  const fallbackLookbackStart = lookbackStartDate(COMMANDER_FALLBACK_LOOKBACK_MONTHS, referenceDate);
  const selectedRows: CommanderUsageRow[] = [];

  for (const topdeckId of topdeckIds) {
    const playerRows = usageRows.filter((row) => row.topdeck_id === topdeckId && row.commander_name && row.start_date);
    const primaryRows = playerRows.filter((row) => row.start_date && row.start_date >= primaryLookbackStart);
    selectedRows.push(...primaryRows);

    if (primaryRows.length >= MIN_PRIMARY_COMMANDER_ENTRIES) continue;

    const fallbackRows = playerRows.filter(
      (row) => row.start_date && row.start_date >= fallbackLookbackStart && row.start_date < primaryLookbackStart
    );
    selectedRows.push(...fallbackRows);

    if (primaryRows.length + fallbackRows.length > 0) continue;

    const lastKnownRow = latestUsageRow(
      playerRows.filter((row) => row.start_date && row.start_date < fallbackLookbackStart)
    );
    if (lastKnownRow) {
      selectedRows.push(lastKnownRow);
    }
  }

  return selectedRows;
}
