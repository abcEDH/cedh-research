import { supabase } from "@/lib/supabase";
import { withTiming } from "@/lib/performance";
import type { PlayerGameLog } from "./player-stats";

const SUPABASE_PAGE_SIZE = 1000;
const SUPABASE_IN_CHUNK_SIZE = 100;

export type PlayerRow = {
  id: string;
  name: string;
  topdeck_id: string;
};

type EntryRow = {
  id: string;
  tournament_id: string;
  player_id: string;
  commander_id: string | null;
};

type CommanderRow = {
  id: string;
  name: string;
};

type ParticipantRow = {
  game_id: string;
  entry_id: string;
  seat_position: number;
  result: string;
};

type GameRow = {
  id: string;
  tournament_id: string;
  round_number: number | null;
  round_name: string | null;
  table_number: number | null;
  is_draw: boolean;
  winner_id: string | null;
};

type TournamentRow = {
  id: string;
  name: string;
  start_date: string;
  state: string | null;
};

type PlayerEventLogRow = {
  game_id: string;
  game_date: string | null;
  tournament_name: string | null;
  state: string | null;
  round_number: number | null;
  round_name: string | null;
  table_number: number | null;
  seat_position: number | null;
  commander_name: string | null;
  game_result: string;
};

type PlayerEventOpponentRow = {
  game_id: string;
  player_id: string;
  player_name: string | null;
  topdeck_id: string | null;
  seat_position: number | null;
  commander_name: string | null;
  game_result: string;
};

function chunkArray<T>(values: T[], chunkSize: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += chunkSize) {
    chunks.push(values.slice(index, index + chunkSize));
  }
  return chunks;
}

function chunkValues<T>(values: T[], size = SUPABASE_IN_CHUNK_SIZE) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += size) {
    chunks.push(values.slice(index, index + size));
  }
  return chunks;
}

function describeSupabaseError(error: unknown) {
  if (!error) return "unknown error";
  if (error instanceof Error) return error.message;
  if (typeof error === "object") {
    const details = error as { message?: string; code?: string; details?: string; hint?: string };
    return [details.message, details.code, details.details, details.hint].filter(Boolean).join(" | ") || JSON.stringify(error);
  }
  return String(error);
}

function toRoundLabel(game: GameRow) {
  if (game.round_name) return game.round_name;
  if (game.round_number !== null) return `Round ${game.round_number}`;
  return "Bracket";
}

function toEventRoundLabel(row: PlayerEventLogRow) {
  if (row.round_name) return row.round_name;
  if (row.round_number !== null) return `Round ${row.round_number}`;
  return "Bracket";
}

export async function fetchPlayer(topdeckId: string): Promise<PlayerRow | null> {
  return withTiming("player-log-data:fetch-player", async () => {
    const { data } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .eq("topdeck_id", topdeckId)
      .maybeSingle();

    return (data as PlayerRow | null) ?? null;
  });
}

async function fetchEntries(playerId: string): Promise<EntryRow[]> {
  const rows: EntryRow[] = [];
  for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
    const { data, error } = await supabase
      .from("tournament_entries")
      .select("id, tournament_id, player_id, commander_id")
      .eq("player_id", playerId)
      .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

    if (error) throw new Error(`Error fetching player entries: ${error.message}`);
    rows.push(...((data as EntryRow[]) ?? []));
    if (!data || data.length < SUPABASE_PAGE_SIZE) break;
  }

  return rows;
}

async function fetchGamesAndParticipants(entryIds: string[]) {
  const participantChunks = await Promise.all(
    chunkValues(entryIds).map(async (entryIdChunk) => {
      const chunkRows: ParticipantRow[] = [];
      for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
        const { data, error } = await supabase
          .from("game_participants")
          .select("game_id, entry_id, seat_position, result")
          .in("entry_id", entryIdChunk)
          .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

        if (error) throw new Error(`Error fetching player game participants: ${error.message}`);
        chunkRows.push(...((data as ParticipantRow[]) ?? []));
        if (!data || data.length < SUPABASE_PAGE_SIZE) break;
      }
      return chunkRows;
    })
  );

  const participants = participantChunks.flat();
  const gameIds = Array.from(new Set(participants.map((row) => row.game_id)));
  if (gameIds.length === 0) {
    return {
      participants: [],
      games: [] as GameRow[],
      allParticipants: [] as ParticipantRow[],
    };
  }

  const [gameChunks, allParticipantChunks] = await Promise.all([
    Promise.all(
      chunkValues(gameIds).map(async (gameIdChunk) => {
        const chunkRows: GameRow[] = [];
        for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
          const { data, error } = await supabase
            .from("games")
            .select("id, tournament_id, round_number, round_name, table_number, is_draw, winner_id")
            .in("id", gameIdChunk)
            .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

          if (error) throw new Error(`Error fetching player games: ${error.message}`);
          chunkRows.push(...((data as GameRow[]) ?? []));
          if (!data || data.length < SUPABASE_PAGE_SIZE) break;
        }
        return chunkRows;
      })
    ),
    Promise.all(
      chunkValues(gameIds).map(async (gameIdChunk) => {
        const chunkRows: ParticipantRow[] = [];
        for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
          const { data, error } = await supabase
            .from("game_participants")
            .select("game_id, entry_id, seat_position, result")
            .in("game_id", gameIdChunk)
            .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

          if (error) throw new Error(`Error fetching pod participants: ${error.message}`);
          chunkRows.push(...((data as ParticipantRow[]) ?? []));
          if (!data || data.length < SUPABASE_PAGE_SIZE) break;
        }
        return chunkRows;
      })
    ),
  ]);

  return {
    participants,
    games: gameChunks.flat(),
    allParticipants: allParticipantChunks.flat(),
  };
}

async function fetchTournaments(tournamentIds: string[]): Promise<Map<string, TournamentRow>> {
  if (tournamentIds.length === 0) return new Map();

  const rows: TournamentRow[] = [];
  for (const tournamentIdChunk of chunkValues(tournamentIds)) {
    const { data, error } = await supabase
      .from("tournaments")
      .select("id, name, start_date, state")
      .in("id", tournamentIdChunk);

    if (error) throw new Error(`Error fetching tournaments: ${error.message}`);
    rows.push(...((data as TournamentRow[]) ?? []));
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchEntriesById(entryIds: string[]): Promise<Map<string, EntryRow>> {
  if (entryIds.length === 0) return new Map();

  const rows: EntryRow[] = [];
  for (const entryIdChunk of chunkValues(entryIds)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("tournament_entries")
        .select("id, tournament_id, player_id, commander_id")
        .in("id", entryIdChunk)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (error) throw new Error(`Error fetching related tournament entries: ${error.message}`);
      rows.push(...((data as EntryRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchPlayersById(playerIds: string[]): Promise<Map<string, PlayerRow>> {
  if (playerIds.length === 0) return new Map();

  const rows: PlayerRow[] = [];
  for (const playerIdChunk of chunkValues(playerIds)) {
    const { data, error } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .in("id", playerIdChunk);

    if (error) throw new Error(`Error fetching related players: ${error.message}`);
    rows.push(...((data as PlayerRow[]) ?? []));
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchCommandersById(commanderIds: string[]): Promise<Map<string, CommanderRow>> {
  if (commanderIds.length === 0) return new Map();

  const rows: CommanderRow[] = [];
  for (const commanderIdChunk of chunkValues(commanderIds)) {
    const { data, error } = await supabase
      .from("commanders")
      .select("id, name")
      .in("id", commanderIdChunk);

    if (error) throw new Error(`Error fetching related commanders: ${error.message}`);
    rows.push(...((data as CommanderRow[]) ?? []));
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function buildPlayerLogsFromRawHistory(entries: EntryRow[]): Promise<PlayerGameLog[]> {
  const entryIds = entries.map((row) => row.id);
  const { participants, games, allParticipants } = await fetchGamesAndParticipants(entryIds);

  const gamesById = new Map(games.map((row) => [row.id, row]));
  const entryById = new Map(entries.map((row) => [row.id, row]));
  const tournamentIds = Array.from(new Set(games.map((row) => row.tournament_id)));

  const playerParticipants = participants.filter((participant) => {
    if (!gamesById.has(participant.game_id)) return false;
    return true;
  });
  const playerGameIds = Array.from(new Set(playerParticipants.map((row) => row.game_id)));
  const relatedParticipants = allParticipants.filter((row) => playerGameIds.includes(row.game_id));
  const relatedEntryIds = Array.from(new Set(relatedParticipants.map((row) => row.entry_id)));

  const [tournamentsById, relatedEntriesById] = await Promise.all([
    fetchTournaments(tournamentIds),
    fetchEntriesById(relatedEntryIds),
  ]);

  const relatedPlayerIds = Array.from(
    new Set(Array.from(relatedEntriesById.values()).map((row) => row.player_id))
  );
  const relatedCommanderIds = Array.from(
    new Set(
      Array.from(relatedEntriesById.values())
        .map((row) => row.commander_id)
        .filter((value): value is string => Boolean(value))
    )
  );

  const [playersById, commandersById] = await Promise.all([
    fetchPlayersById(relatedPlayerIds),
    fetchCommandersById(relatedCommanderIds),
  ]);

  return playerParticipants
    .map((participant) => {
      const game = gamesById.get(participant.game_id);
      const playerEntry = entryById.get(participant.entry_id);
      if (!game || !playerEntry) return null;

      const tournament = tournamentsById.get(game.tournament_id);
      const commanderName = playerEntry.commander_id
        ? commandersById.get(playerEntry.commander_id)?.name ?? null
        : null;
      const pod = relatedParticipants
        .filter((row) => row.game_id === participant.game_id && row.entry_id !== participant.entry_id)
        .map((row) => {
          const opponentEntry = relatedEntriesById.get(row.entry_id);
          const opponentPlayer = opponentEntry ? playersById.get(opponentEntry.player_id) : null;
          const opponentCommander = opponentEntry?.commander_id
            ? commandersById.get(opponentEntry.commander_id)?.name ?? null
            : null;

          return {
            topdeckId: opponentPlayer?.topdeck_id ?? null,
            playerName: opponentPlayer?.name ?? "Unknown",
            commanderName: opponentCommander,
            seat: row.seat_position + 1,
            result: row.result,
          };
        })
        .sort((a, b) => a.seat - b.seat);

      return {
        gameId: participant.game_id,
        startDate: tournament?.start_date ?? "",
        tournamentName: tournament?.name ?? "Unknown tournament",
        state: tournament?.state ?? null,
        roundLabel: toRoundLabel(game),
        tableLabel: game.table_number !== null ? `Table ${game.table_number}` : "Bracket",
        seat: participant.seat_position + 1,
        result: participant.result,
        commanderName,
        opponents: pod,
      } satisfies PlayerGameLog;
    })
    .filter((value): value is PlayerGameLog => Boolean(value))
    .sort((a, b) => b.startDate.localeCompare(a.startDate));
}

async function fetchPlayerEventLogs(playerId: string, regionFilter: string): Promise<PlayerGameLog[]> {
  const eventLogTables = ["global_elo_game_event_log", "regional_elo_game_event_log"];
  let eventRows: PlayerEventLogRow[] = [];
  let eventLogTable = eventLogTables[0];
  let lastEventError: unknown = null;

  for (const table of eventLogTables) {
    const collected: PlayerEventLogRow[] = [];
    let queryFailed = false;
    let queryError: unknown = null;

    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      let query = supabase
        .from(table)
        .select(
          "game_id, game_date, tournament_name, state, round_number, round_name, table_number, seat_position, commander_name, game_result"
        )
        .eq("player_id", playerId)
        .order("game_date", { ascending: false })
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (regionFilter) {
        query = query.ilike("state", regionFilter);
      }

      const { data, error } = await query;
      if (error) {
        queryFailed = true;
        queryError = error;
        break;
      }

      collected.push(...((data as PlayerEventLogRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }

    if (!queryFailed) {
      eventRows = collected;
      eventLogTable = table;
      break;
    }
    lastEventError = queryError;
  }

  if (lastEventError && eventRows.length === 0 && eventLogTable === eventLogTables[0]) {
    console.error("Error fetching precomputed player event log:", describeSupabaseError(lastEventError));
    return [];
  }
  if (eventRows.length === 0) return [];

  const gameIds = Array.from(new Set(eventRows.map((row) => row.game_id)));
  const opponentRows: PlayerEventOpponentRow[] = [];
  const opponentChunks = await Promise.all(
    chunkArray(gameIds, 250).map(async (gameIdChunk) => {
      const chunkRows: PlayerEventOpponentRow[] = [];
      for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
        const { data: opponentData, error: opponentError } = await supabase
          .from(eventLogTable)
          .select("game_id, player_id, player_name, topdeck_id, seat_position, commander_name, game_result")
          .in("game_id", gameIdChunk)
          .neq("player_id", playerId)
          .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

        if (opponentError) {
          console.error(
            "Error fetching precomputed player event opponents:",
            describeSupabaseError(opponentError)
          );
          break;
        }
        chunkRows.push(...((opponentData as PlayerEventOpponentRow[]) ?? []));
        if (!opponentData || opponentData.length < SUPABASE_PAGE_SIZE) break;
      }
      return chunkRows;
    })
  );

  for (const chunk of opponentChunks) {
    opponentRows.push(...chunk);
  }

  const opponentsByGameId = new Map<string, PlayerGameLog["opponents"]>();
  for (const row of opponentRows) {
    const existing = opponentsByGameId.get(row.game_id) ?? [];
    existing.push({
      topdeckId: row.topdeck_id,
      playerName: row.player_name ?? "Unknown",
      commanderName: row.commander_name,
      seat: (row.seat_position ?? 0) + 1,
      result: row.game_result,
    });
    opponentsByGameId.set(row.game_id, existing);
  }
  for (const opponents of opponentsByGameId.values()) {
    opponents.sort((a, b) => a.seat - b.seat);
  }

  return eventRows.map((row) => ({
    gameId: row.game_id,
    startDate: row.game_date ?? "",
    tournamentName: row.tournament_name ?? "Unknown tournament",
    state: row.state,
    roundLabel: toEventRoundLabel(row),
    tableLabel: row.table_number !== null ? `Table ${row.table_number}` : "Bracket",
    seat: (row.seat_position ?? 0) + 1,
    result: row.game_result,
    commanderName: row.commander_name,
    opponents: opponentsByGameId.get(row.game_id) ?? [],
  }));
}

export async function fetchCanonicalPlayerLogs(playerId: string, regionFilter = ""): Promise<PlayerGameLog[]> {
  const eventLogs = await fetchPlayerEventLogs(playerId, regionFilter);
  if (eventLogs.length > 0) return eventLogs;
  const entries = await fetchEntries(playerId);
  return buildPlayerLogsFromRawHistory(entries);
}
