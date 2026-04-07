import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { supabase } from "@/lib/supabase";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { normalizeDisplayString } from "@/lib/utils";
import { summarizePlayerLogs, type PlayerGameLog } from "./player-stats";

export const dynamic = "force-dynamic";

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
  primary_region_key?: string | null;
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

function readRegionParam(
  params:
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined
) {
  if (!params) return "";
  if (typeof (params as URLSearchParams).get === "function") {
    return (params as URLSearchParams).get("region") ?? "";
  }
  const value = (params as Record<string, string | string[] | undefined>).region;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatResult(result: string) {
  return result.charAt(0).toUpperCase() + result.slice(1);
}

function toRoundLabel(game: GameRow) {
  if (game.round_name) return game.round_name;
  if (game.round_number !== null) return `Round ${game.round_number}`;
  return "Bracket";
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

async function fetchRegionalRank(playerId: string, regionKey: string): Promise<LeaderboardRankRow | null> {
  if (!regionKey) return null;

  const { data } = await supabase
    .from("regional_elo_leaderboard")
    .select("rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "state")
    .eq("region_key", regionKey)
    .eq("player_id", playerId)
    .maybeSingle();

  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchGlobalRank(playerId: string): Promise<LeaderboardRankRow | null> {
  const { data } = await supabase
    .from("regional_elo_leaderboard")
    .select("primary_region_key, rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "global")
    .eq("region_key", "ALL")
    .eq("player_id", playerId)
    .maybeSingle();

  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchRegionalRanks(playerId: string): Promise<LeaderboardRankRow[]> {
  const { data } = await supabase
    .from("regional_elo_leaderboard")
    .select("region_key, rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "state")
    .eq("player_id", playerId)
    .order("rank", { ascending: true });

  return ((data as LeaderboardRankRow[]) ?? []).sort((a, b) => {
    if (a.rank !== b.rank) return a.rank - b.rank;
    return (a.region_key ?? "").localeCompare(b.region_key ?? "");
  });
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
  searchParams,
}: {
  params: Promise<{ topdeckId: string }> | { topdeckId: string };
  searchParams?:
    | Promise<{ region?: string | string[] }>
    | { region?: string | string[] };
}) {
  const resolvedParams = await Promise.resolve(params);
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const topdeckId = resolvedParams.topdeckId;
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim().toUpperCase();
  const regionFilter = requestedRegion === "ALL" ? "" : requestedRegion;

  const player = await fetchPlayer(topdeckId);
  if (!player) {
    return (
      <main className="container mx-auto px-4 py-10">
        <p className="text-sm text-muted-foreground">No player found for TopDeck ID {topdeckId}.</p>
      </main>
    );
  }

  const [globalRank, regionalRank, regionalRanks, globalSnapshot, entries] = await Promise.all([
    fetchGlobalRank(player.id),
    fetchRegionalRank(player.id, regionFilter),
    fetchRegionalRanks(player.id),
    fetchGlobalSnapshot(topdeckId),
    fetchEntries(player.id),
  ]);
  const entryIds = entries.map((row) => row.id);
  const { participants, games, allParticipants } = await fetchGamesAndParticipants(entryIds);

  const gamesById = new Map(games.map((row) => [row.id, row]));
  const entryById = new Map(entries.map((row) => [row.id, row]));
  const tournamentIds = Array.from(new Set(games.map((row) => row.tournament_id)));
  const tournamentsById = await fetchTournaments(tournamentIds);

  const filteredParticipants = participants.filter((participant) => {
    if (!regionFilter) return true;
    const game = gamesById.get(participant.game_id);
    const tournament = game ? tournamentsById.get(game.tournament_id) : null;
    return ((tournament?.state ?? "").trim().toUpperCase() || "") === regionFilter;
  });

  const filteredGameIds = Array.from(new Set(filteredParticipants.map((row) => row.game_id)));
  const relatedParticipants = allParticipants.filter((row) => filteredGameIds.includes(row.game_id));
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

  const playerLogs = filteredParticipants
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

  const { totalGames, totalWins, totalDraws, totalLosses, seatRows, opponentRecords } =
    summarizePlayerLogs(playerLogs);
  const homeRegion = globalRank?.primary_region_key ?? regionalRanks[0]?.region_key ?? null;
  const activeRank = regionFilter ? regionalRank : globalRank;
  const canonicalGames = activeRank?.games_played ?? totalGames;
  const canonicalWins = activeRank?.wins ?? totalWins;
  const canonicalDraws = activeRank?.draws ?? totalDraws;
  const canonicalLosses = activeRank?.losses ?? totalLosses;
  const topdeckProfileHref = buildTopdeckProfileHref(topdeckId);
  const backHref = regionFilter
    ? `/regional-elo?scope=state&region=${encodeURIComponent(regionFilter)}`
    : "/regional-elo";

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8">
          <div className="space-y-3">
            <Link href={backHref} className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to leaderboard
            </Link>
            <p className="knd-chip">Leaderboard Player Drilldown</p>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
                  {player.name}
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Home region is assigned from recent and sustained activity, but this page defaults
                  to the global view. Use the region filter below to inspect a specific state slice.
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

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Home Region
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {homeRegion ?? "Unassigned"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Current Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {activeRank ? `#${activeRank.rank}` : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  TopDeck Global
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
                  View Filter
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <form method="get" className="space-y-2">
                  <label className="text-xs text-muted-foreground" htmlFor="region-filter">
                    Region
                  </label>
                  <select
                    id="region-filter"
                    name="region"
                    defaultValue={regionFilter || "ALL"}
                    className="knd-input"
                  >
                    <option value="ALL">ALL</option>
                    {regionalRanks
                      .map((row) => row.region_key)
                      .filter((value): value is string => Boolean(value))
                      .map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                  </select>
                  <button
                    type="submit"
                    className="w-full rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
                  >
                    Apply filter
                  </button>
                </form>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Counted Games
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {canonicalGames}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Record
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {canonicalWins}-{canonicalLosses}-{canonicalDraws}
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
            Elo is global. Home region is assigned separately. The summary cards and game log below
            reflect the active filter, which defaults to all games unless you narrow to a state.
          </p>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                State Assignment
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                This player will usually appear in one assigned state. If their activity shifts over time,
                their assignment can move on the next recompute.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Region</th>
                      <th className="px-2 py-3 text-right">Rank</th>
                      <th className="px-2 py-3 text-right">Elo</th>
                      <th className="px-2 py-3 text-right">Games</th>
                      <th className="px-2 py-3 text-right">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {regionalRanks.map((row) => {
                      const regionKey = row.region_key ?? "";
                      const isActive = regionKey === regionFilter;
                      return (
                        <tr key={regionKey} className="border-t border-border/60">
                          <td className="px-2 py-3">
                            <Link
                              href={`/regional-elo/player/${topdeckId}?region=${encodeURIComponent(regionKey)}`}
                              className={
                                isActive
                                  ? "font-semibold text-foreground hover:text-primary"
                                  : "text-foreground hover:text-primary"
                              }
                            >
                              {regionKey}
                            </Link>
                            {regionKey === homeRegion ? (
                              <div className="text-[11px] text-primary">Assigned state</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-foreground">#{row.rank}</td>
                          <td className="px-2 py-3 text-right font-mono text-foreground">
                            {Math.round(row.rating)}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.games_played}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      );
                    })}
                    {regionalRanks.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No state assignment found for this player.
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
                  Opponent Records
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <tr>
                        <th className="px-2 py-3">Opponent</th>
                        <th className="px-2 py-3 text-right">Games</th>
                        <th className="px-2 py-3 text-right">W-L-D</th>
                      </tr>
                    </thead>
                    <tbody>
                      {opponentRecords.map((record) => (
                        <tr key={`${record.opponentTopdeckId ?? record.opponentName}`} className="border-t border-border/60">
                          <td className="px-2 py-3">
                            {record.opponentTopdeckId ? (
                              <Link
                                href={
                                  regionFilter
                                    ? `/regional-elo/player/${record.opponentTopdeckId}?region=${encodeURIComponent(regionFilter)}`
                                    : `/regional-elo/player/${record.opponentTopdeckId}`
                                }
                                className="font-medium text-foreground hover:text-primary"
                              >
                                {record.opponentName}
                              </Link>
                            ) : (
                              <span className="font-medium text-foreground">{record.opponentName}</span>
                            )}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {record.games}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {record.wins}-{record.losses}-{record.draws}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Counted Games
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                These are the exact games included by the active filter for this player. By default
                the view is global and shows all tracked games; choosing a state narrows the log to that region.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Date</th>
                      <th className="px-2 py-3">Tournament</th>
                      <th className="px-2 py-3">Round</th>
                      <th className="px-2 py-3">Seat</th>
                      <th className="px-2 py-3">Result</th>
                      <th className="px-2 py-3">Commander</th>
                      <th className="px-2 py-3">Opponents</th>
                    </tr>
                  </thead>
                  <tbody>
                    {playerLogs.map((log) => (
                      <tr key={log.gameId} className="border-t border-border/60 align-top">
                        <td className="px-2 py-3 text-muted-foreground">{formatDate(log.startDate)}</td>
                        <td className="px-2 py-3">
                          <div className="font-medium text-foreground">{log.tournamentName}</div>
                          <div className="text-xs text-muted-foreground">{log.state || "—"}</div>
                        </td>
                        <td className="px-2 py-3 text-muted-foreground">
                          {log.roundLabel}
                          <div className="text-xs">{log.tableLabel}</div>
                        </td>
                        <td className="px-2 py-3 text-muted-foreground">Seat {log.seat}</td>
                        <td className="px-2 py-3 font-medium text-foreground">{formatResult(log.result)}</td>
                        <td className="px-2 py-3 text-muted-foreground">
                          {log.commanderName ? normalizeDisplayString(log.commanderName) : "Unknown commander"}
                        </td>
                        <td className="px-2 py-3 text-xs text-muted-foreground">
                          <div className="space-y-1">
                            {log.opponents.map((opponent) => (
                              <div key={`${log.gameId}:${opponent.seat}`}>
                                Seat {opponent.seat}: {opponent.playerName}
                                {opponent.commanderName
                                  ? ` · ${normalizeDisplayString(opponent.commanderName)}`
                                  : ""}
                                {` · ${formatResult(opponent.result)}`}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
