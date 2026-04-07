import Link from "next/link";
import { unstable_cache } from "next/cache";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import { predictNextState, type PlayerStateHistoryRow } from "@/lib/player-region-predictor";
import { supabase } from "@/lib/supabase";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { OpponentRecordsTable } from "./opponent-records-table";
import { PlayerGamesTable } from "./player-games-table";
import { summarizePlayerLogs, type PlayerGameLog } from "./player-stats";

export const dynamic = "force-dynamic";
const COMMANDER_LOOKBACK_MONTHS = 6;
const COMMANDER_FALLBACK_LOOKBACK_MONTHS = 12;
const MIN_PRIMARY_COMMANDER_ENTRIES = 2;

type PlayerRow = {
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

type LeaderboardRankRow = {
  region_key?: string;
  rank: number;
  rating: number;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

type GlobalSnapshotRow = {
  rank: number;
  points: number;
};

type GlobalEloLeaderboardRow = {
  player_id: string;
  topdeck_id: string | null;
  rating: number;
  games_played: number;
};

type PlayerStateHistoryQueryRow = {
  players:
    | {
        topdeck_id: string | null;
      }
    | Array<{
        topdeck_id: string | null;
      }>
    | null;
  tournaments:
    | {
        start_date: string | null;
        state: string | null;
        player_count: number | null;
      }
    | Array<{
        start_date: string | null;
        state: string | null;
        player_count: number | null;
      }>
    | null;
};

function toRoundLabel(game: GameRow) {
  if (game.round_name) return game.round_name;
  if (game.round_number !== null) return `Round ${game.round_number}`;
  return "Bracket";
}

function normalizeState(value: string | null | undefined) {
  return (value ?? "").trim().toUpperCase();
}

function isKnownCommanderName(value: string | null | undefined) {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

function firstRelation<T>(value: T | T[] | null) {
  return Array.isArray(value) ? value[0] ?? null : value;
}

async function fetchPlayer(topdeckId: string): Promise<PlayerRow | null> {
  const { data } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .eq("topdeck_id", topdeckId)
    .maybeSingle();

  return (data as PlayerRow | null) ?? null;
}

async function fetchEntries(playerId: string): Promise<EntryRow[]> {
  const { data } = await supabase
    .from("tournament_entries")
    .select("id, tournament_id, player_id, commander_id")
    .eq("player_id", playerId);

  return (data as EntryRow[]) ?? [];
}

async function fetchPlayerStateHistory(playerId: string): Promise<PlayerStateHistoryRow[]> {
  const { data } = await supabase
    .from("tournament_entries")
    .select("tournaments!inner(start_date, state, player_count)")
    .eq("player_id", playerId)
    .not("tournaments.state", "is", null)
    .not("tournaments.start_date", "is", null);

  return ((data as Array<{
    tournaments:
      | {
          start_date: string | null;
          state: string | null;
          player_count: number | null;
        }
      | Array<{
          start_date: string | null;
          state: string | null;
          player_count: number | null;
        }>
      | null;
  }> | null) ?? [])
    .map((row) => {
      const tournament = Array.isArray(row.tournaments) ? row.tournaments[0] : row.tournaments;
      if (!tournament?.start_date || !tournament.state) return null;
      return {
        start_date: tournament.start_date,
        state: tournament.state,
        player_count: tournament.player_count,
      };
    })
    .filter((row): row is PlayerStateHistoryRow => Boolean(row));
}

async function fetchGlobalEloRank(playerId: string): Promise<LeaderboardRankRow | null> {
  const { data } = await supabase
    .from("regional_elo_leaderboard")
    .select("rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "global")
    .eq("region_key", "ALL")
    .eq("player_id", playerId)
    .maybeSingle();

  return (data as LeaderboardRankRow | null) ?? null;
}

const fetchPredictedRegionByPlayer = unstable_cache(
  async (): Promise<Record<string, string>> => {
    const pageSize = 1000;
    const histories = new Map<string, PlayerStateHistoryRow[]>();

    for (let offset = 0; ; offset += pageSize) {
      const { data, error } = await supabase
        .from("tournament_entries")
        .select("players!inner(topdeck_id), tournaments!inner(start_date, state, player_count)")
        .not("players.topdeck_id", "is", null)
        .not("tournaments.state", "is", null)
        .not("tournaments.start_date", "is", null)
        .range(offset, offset + pageSize - 1);

      if (error || !data?.length) break;

      for (const row of data as PlayerStateHistoryQueryRow[]) {
        const player = firstRelation(row.players);
        const tournament = firstRelation(row.tournaments);
        if (!player?.topdeck_id || !tournament?.state || !tournament.start_date) continue;
        const playerRows = histories.get(player.topdeck_id) ?? [];
        playerRows.push({
          state: tournament.state,
          start_date: tournament.start_date,
          player_count: tournament.player_count,
        });
        histories.set(player.topdeck_id, playerRows);
      }

      if (data.length < pageSize) break;
    }

    const predictions: Record<string, string> = {};
    for (const [topdeckId, rows] of histories.entries()) {
      const prediction = predictNextState(rows);
      if (prediction) {
        predictions[topdeckId] = prediction.state;
      }
    }
    return predictions;
  },
  ["regional-elo-predicted-player-regions-v1"],
  { revalidate: 60 * 15 }
);

async function fetchGlobalEloLeaderboardRows(): Promise<GlobalEloLeaderboardRow[]> {
  const pageSize = 1000;
  const rows: GlobalEloLeaderboardRow[] = [];

  for (let offset = 0; ; offset += pageSize) {
    const { data, error } = await supabase
      .from("regional_elo_leaderboard")
      .select("player_id, topdeck_id, rating, games_played")
      .eq("region_type", "global")
      .eq("region_key", "ALL")
      .order("rating", { ascending: false })
      .range(offset, offset + pageSize - 1);

    if (error || !data?.length) break;
    rows.push(...(data as GlobalEloLeaderboardRow[]));
    if (data.length < pageSize) break;
  }

  return rows;
}

async function fetchProfileRegionRank(playerId: string, region: string) {
  if (!region) return null;

  const [globalRows, predictedRegionByPlayer] = await Promise.all([
    fetchGlobalEloLeaderboardRows(),
    fetchPredictedRegionByPlayer(),
  ]);
  const regionRows = globalRows.filter(
    (row) => row.topdeck_id && predictedRegionByPlayer[row.topdeck_id] === region
  );
  const index = regionRows.findIndex((row) => row.player_id === playerId);
  return index >= 0 ? index + 1 : null;
}

async function fetchGlobalSnapshot(topdeckId: string): Promise<GlobalSnapshotRow | null> {
  try {
    const leaderboard = await fetchChampionshipLeaderboard();
    const entry = leaderboard.find((row) => row.uid === topdeckId);
    if (!entry) return null;
    return {
      rank: entry.rank,
      points: entry.points,
    };
  } catch {
    return null;
  }
}

async function fetchActiveCommander(topdeckId: string): Promise<string | null> {
  const referenceDate = new Date();
  const lookbackStart = lookbackStartDate(COMMANDER_LOOKBACK_MONTHS, referenceDate);
  const fallbackLookbackStart = lookbackStartDate(COMMANDER_FALLBACK_LOOKBACK_MONTHS, referenceDate);
  const primaryUsageRows = await getCommanderUsageRows([topdeckId], lookbackStart);
  const primaryEntryCount = primaryUsageRows.filter((row) => row.topdeck_id && row.commander_name).length;
  const fallbackUsageRows =
    primaryEntryCount < MIN_PRIMARY_COMMANDER_ENTRIES
      ? await getCommanderUsageRows([topdeckId], fallbackLookbackStart, lookbackStart)
      : [];
  const profiles = buildProfiles(
    [topdeckId],
    [...primaryUsageRows, ...fallbackUsageRows],
    1,
    referenceDate.toISOString()
  );

  return profiles.players[0]?.commanders[0]?.commander ?? null;
}

async function fetchGamesAndParticipants(entryIds: string[]) {
  const { data: participantData } = await supabase
    .from("game_participants")
    .select("game_id, entry_id, seat_position, result")
    .in("entry_id", entryIds);

  const participants = (participantData as ParticipantRow[]) ?? [];
  const gameIds = Array.from(new Set(participants.map((row) => row.game_id)));
  if (gameIds.length === 0) {
    return {
      participants: [],
      games: [] as GameRow[],
      allParticipants: [] as ParticipantRow[],
    };
  }

  const [{ data: gameData }, { data: allParticipantData }] = await Promise.all([
    supabase
      .from("games")
      .select("id, tournament_id, round_number, round_name, table_number, is_draw, winner_id")
      .in("id", gameIds),
    supabase
      .from("game_participants")
      .select("game_id, entry_id, seat_position, result")
      .in("game_id", gameIds),
  ]);

  return {
    participants,
    games: (gameData as GameRow[]) ?? [],
    allParticipants: (allParticipantData as ParticipantRow[]) ?? [],
  };
}

async function fetchTournaments(tournamentIds: string[]): Promise<Map<string, TournamentRow>> {
  if (tournamentIds.length === 0) return new Map();

  const { data } = await supabase
    .from("tournaments")
    .select("id, name, start_date, state")
    .in("id", tournamentIds);

  return new Map(((data as TournamentRow[]) ?? []).map((row) => [row.id, row]));
}

async function fetchEntriesById(entryIds: string[]): Promise<Map<string, EntryRow>> {
  if (entryIds.length === 0) return new Map();

  const { data } = await supabase
    .from("tournament_entries")
    .select("id, tournament_id, player_id, commander_id")
    .in("id", entryIds);

  return new Map(((data as EntryRow[]) ?? []).map((row) => [row.id, row]));
}

async function fetchPlayersById(playerIds: string[]): Promise<Map<string, PlayerRow>> {
  if (playerIds.length === 0) return new Map();

  const { data } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .in("id", playerIds);

  return new Map(((data as PlayerRow[]) ?? []).map((row) => [row.id, row]));
}

async function fetchCommandersById(commanderIds: string[]): Promise<Map<string, CommanderRow>> {
  if (commanderIds.length === 0) return new Map();

  const { data } = await supabase
    .from("commanders")
    .select("id, name")
    .in("id", commanderIds);

  return new Map(((data as CommanderRow[]) ?? []).map((row) => [row.id, row]));
}

export default async function RegionalPlayerPage({
  params,
}: {
  params: Promise<{ topdeckId: string }> | { topdeckId: string };
}) {
  const resolvedParams = await Promise.resolve(params);
  const topdeckId = resolvedParams.topdeckId;

  const player = await fetchPlayer(topdeckId);
  if (!player) {
    return (
      <main className="container mx-auto px-4 py-10">
        <p className="text-sm text-muted-foreground">No player found for TopDeck ID {topdeckId}.</p>
      </main>
    );
  }

  const [globalSnapshot, globalEloRank, entries, stateHistory, activeCommander] = await Promise.all([
    fetchGlobalSnapshot(topdeckId),
    fetchGlobalEloRank(player.id),
    fetchEntries(player.id),
    fetchPlayerStateHistory(player.id),
    fetchActiveCommander(topdeckId),
  ]);
  const predictedState = predictNextState(stateHistory);
  const selectedRegion = predictedState?.state ?? "";
  const profileRegionRank = await fetchProfileRegionRank(player.id, selectedRegion);
  const entryIds = entries.map((row) => row.id);
  const { participants, games, allParticipants } = await fetchGamesAndParticipants(entryIds);

  const gamesById = new Map(games.map((row) => [row.id, row]));
  const entryById = new Map(entries.map((row) => [row.id, row]));
  const tournamentIds = Array.from(new Set(games.map((row) => row.tournament_id)));
  const tournamentsById = await fetchTournaments(tournamentIds);

  const playerParticipants = participants.filter((participant) => gamesById.has(participant.game_id));
  const playerGameIds = Array.from(new Set(playerParticipants.map((row) => row.game_id)));
  const relatedParticipants = allParticipants.filter((row) => playerGameIds.includes(row.game_id));
  const relatedEntryIds = Array.from(new Set(relatedParticipants.map((row) => row.entry_id)));
  const relatedEntriesById = await fetchEntriesById(relatedEntryIds);
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
  const playersById = await fetchPlayersById(relatedPlayerIds);
  const commandersById = await fetchCommandersById(relatedCommanderIds);

  const playerLogs = playerParticipants
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

  const { totalGames, seatRows, opponentRecords } = summarizePlayerLogs(playerLogs);
  const commanderRows = Array.from(
    playerLogs.reduce(
      (rows, log) => {
        if (!isKnownCommanderName(log.commanderName)) return rows;
        const commander = log.commanderName as string;
        const current = rows.get(commander) ?? {
          commander,
          games: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          latestDate: "",
        };
        current.games += 1;
        if (log.result === "win") {
          current.wins += 1;
        } else if (log.result === "draw") {
          current.draws += 1;
        } else if (log.result === "loss") {
          current.losses += 1;
        }
        if (log.startDate > current.latestDate) {
          current.latestDate = log.startDate;
        }
        rows.set(commander, current);
        return rows;
      },
      new Map<
        string,
        {
          commander: string;
          games: number;
          wins: number;
          draws: number;
          losses: number;
          latestDate: string;
        }
      >()
    ).values()
  ).sort((a, b) => {
    if (b.games !== a.games) return b.games - a.games;
    if (b.latestDate !== a.latestDate) return b.latestDate.localeCompare(a.latestDate);
    return a.commander.localeCompare(b.commander);
  });
  const stateRows = Array.from(
    playerLogs.reduce(
      (rows, log) => {
        const state = normalizeState(log.state) || "UNKNOWN";
        const current = rows.get(state) ?? {
          state,
          games: 0,
          wins: 0,
          draws: 0,
          losses: 0,
        };
        current.games += 1;
        if (log.result === "win") {
          current.wins += 1;
        } else if (log.result === "draw") {
          current.draws += 1;
        } else if (log.result === "loss") {
          current.losses += 1;
        }
        rows.set(state, current);
        return rows;
      },
      new Map<string, { state: string; games: number; wins: number; draws: number; losses: number }>()
    ).values()
  ).sort((a, b) => {
    if (a.state === "UNKNOWN") return 1;
    if (b.state === "UNKNOWN") return -1;
    if (b.games !== a.games) return b.games - a.games;
    return a.state.localeCompare(b.state);
  });
  const topdeckProfileHref = buildTopdeckProfileHref(topdeckId);
  const backHref = selectedRegion ? `/regional-elo?region=${encodeURIComponent(selectedRegion)}` : "/regional-elo";

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8">
          <div className="space-y-3">
            <Link href={backHref} className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to regional leaderboard
            </Link>
            <p className="knd-chip">Regional Elo Player Drilldown</p>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
                  {player.name}
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Showing {totalGames} games from this player&apos;s stored tournament history.
                </p>
              </div>
              {topdeckProfileHref ? (
                <a
                  href={topdeckProfileHref}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-primary hover:text-foreground"
                >
                  Open TopDeck profile
                </a>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-8">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Region
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {predictedState?.state ?? "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  State Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {profileRegionRank ? `#${profileRegionRank}` : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Global Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {globalEloRank ? `#${globalEloRank.rank}` : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  TopDeck Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {globalSnapshot ? `#${globalSnapshot.rank}` : "—"}
                </div>
                <div className="text-sm text-muted-foreground">
                  {globalSnapshot ? `${globalSnapshot.points} points` : "No global snapshot"}
                </div>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Elo
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {globalEloRank ? Math.round(globalEloRank.rating) : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Games
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {totalGames}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Record
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {seatRows.reduce((sum, row) => sum + row.wins, 0)}-
                {seatRows.reduce((sum, row) => sum + row.losses, 0)}-
                {seatRows.reduce((sum, row) => sum + row.draws, 0)}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Opponents
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {opponentRecords.length}
              </CardContent>
            </Card>
          </div>

          <p className="text-sm text-muted-foreground">
            Elo uses the global all-games leaderboard. State Rank uses the active profile region leaderboard.
            Games, record, seats, opponents, and the detailed log use all stored games for this player.
          </p>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Played Commanders
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Commanders from all stored games for this player, sorted by total games.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Commander</th>
                      <th className="px-2 py-3 text-right">Games</th>
                      <th className="px-2 py-3 text-right">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commanderRows.map((row) => {
                      const isActive = activeCommander === row.commander;
                      return (
                        <tr key={row.commander} className="border-t border-border/60">
                          <td className="px-2 py-3">
                            <span className={isActive ? "font-semibold text-foreground" : "text-foreground"}>
                              {row.commander}
                            </span>
                            {isActive ? (
                              <div className="text-[11px] text-primary">Active commander</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.games}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      );
                    })}
                    {commanderRows.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No commander game history found for this player.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Regional Games
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                States where this player has stored game results, sorted by total games.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Region</th>
                      <th className="px-2 py-3 text-right">Games</th>
                      <th className="px-2 py-3 text-right">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stateRows.map((row) => {
                      const isActive = row.state === selectedRegion;
                      return (
                        <tr key={row.state} className="border-t border-border/60">
                          <td className="px-2 py-3">
                            <span className={isActive ? "font-semibold text-foreground" : "text-foreground"}>
                              {row.state}
                            </span>
                            {isActive ? (
                              <div className="text-[11px] text-primary">Active region</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.games}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      );
                    })}
                    {stateRows.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No state-level game history found for this player.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  Seat Distribution
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {seatRows.map((row) => (
                  <div key={row.seat} className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-foreground">Seat {row.seat}</span>
                      <span className="font-mono text-sm text-muted-foreground">{row.games} games</span>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {row.wins}-{row.losses}-{row.draws}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  Record Against Opponents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <OpponentRecordsTable records={opponentRecords} />
              </CardContent>
            </Card>
          </div>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Games
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                These are all stored games found for this player across tournament locations.
              </p>
            </CardHeader>
            <CardContent>
              <PlayerGamesTable logs={playerLogs} />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
