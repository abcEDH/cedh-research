import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { unstable_cache } from "next/cache";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import Link from "next/link";
import { HomeSearchBar } from "@/components/home-search-bar";

const HOME_CACHE_REVALIDATE_SECONDS = 60 * 60 * 6; // 6 hours

export const dynamic = "force-dynamic";

interface TopCommander {
  commander_id: string;
  commander_name: string;
  total_entries: number;
  avg_win_rate: string | number;
  conversion_rate_top_cut: string | number;
  color_identity: string[] | null;
}

interface RisingCommander {
  commander_id: string;
  commander_name: string;
  entries_delta: number;
  meta_share_delta: number;
  recent_entries: number;
  prior_entries: number;
  total_entries: number;
  avg_win_rate: string | number;
  color_identity: string[] | null;
}

function addDaysIso(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00.000Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function isKnownCommanderName(value: string | null | undefined): value is string {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

/**
 * Orders commanders by the largest gain in weekly tournament entries: sums the two most recent
 * ISO weeks from `commander_weekly_trends` and subtracts the sum for the two weeks before that
 * (32+ player events; same filter as the materialized view).
 */
async function getTopRisingCommandersByTwoWeekTrend(): Promise<RisingCommander[]> {
  const { data: maxRows, error: maxErr } = await supabase
    .from("commander_weekly_trends")
    .select("week_start_date")
    .not("commander_name", "ilike", "unknown commander")
    .not("commander_name", "is", null)
    .neq("commander_name", "")
    .order("week_start_date", { ascending: false })
    .limit(1);

  if (maxErr) {
    throw new Error(`Rising commanders max week query failed: ${maxErr.message}`);
  }
  if (!maxRows?.[0]?.week_start_date) return [];

  const latestWeek = maxRows[0].week_start_date as string;
  const windowStart = addDaysIso(latestWeek, -35);

  const { data: trendRows, error: trendErr } = await supabase
    .from("commander_weekly_trends")
    .select("commander_id, commander_name, week_start_date, entries")
    .not("commander_name", "ilike", "unknown commander")
    .not("commander_name", "is", null)
    .neq("commander_name", "")
    .gte("week_start_date", windowStart)
    .lte("week_start_date", latestWeek);

  if (trendErr) {
    throw new Error(`Rising commanders trends window query failed: ${trendErr.message}`);
  }
  if (!trendRows?.length) return [];

  const weekSet = [...new Set(trendRows.map((r) => r.week_start_date as string))].sort((a, b) =>
    b.localeCompare(a)
  );

  if (weekSet.length < 2) return [];

  const recentWeekDates = weekSet.slice(0, 2);
  let priorWeekDates: string[];
  if (weekSet.length >= 4) {
    priorWeekDates = weekSet.slice(2, 4);
  } else if (weekSet.length === 3) {
    priorWeekDates = weekSet.slice(2, 3);
  } else {
    priorWeekDates = [];
  }

  const recentKey = new Set(recentWeekDates);
  const priorKey = new Set(priorWeekDates);

  let recentTotal = 0;
  let priorTotal = 0;
  const totals = new Map<string, { name: string; recent: number; prior: number }>();
  for (const row of trendRows) {
    const id = row.commander_id as string;
    const wk = row.week_start_date as string;
    const n = row.entries ?? 0;
    const cur = totals.get(id) ?? { name: row.commander_name as string, recent: 0, prior: 0 };
    if (recentKey.has(wk)) {
      cur.recent += n;
      recentTotal += n;
    }
    if (priorKey.has(wk)) {
      cur.prior += n;
      priorTotal += n;
    }
    totals.set(id, cur);
  }

  const scored = [...totals.entries()]
    .map(([commander_id, v]) => ({
      commander_id,
      commander_name: v.name,
      entries_delta: v.recent - v.prior,
      meta_share_delta: (v.recent / recentTotal) - (v.prior / priorTotal),
      recent_entries: v.recent,
      prior_entries: v.prior,
    }))
    .filter((x) => x.meta_share_delta > 0)
    .sort((a, b) => b.meta_share_delta - a.meta_share_delta)
    .slice(0, 3);

  if (scored.length === 0) return [];

  const { data: metaRows, error: metaErr } = await supabase
    .from("commander_stats")
    .select("commander_id, color_identity, avg_win_rate, total_entries")
    .in(
      "commander_id",
      scored.map((s) => s.commander_id)
    );

  if (metaErr) {
    throw new Error(`Rising commanders enrich query failed: ${metaErr.message}`);
  }

  const metaById = new Map((metaRows ?? []).map((m) => [m.commander_id as string, m]));

  return scored.map((s) => {
    const meta = metaById.get(s.commander_id);
    const wr = meta?.avg_win_rate;
    const avg_win_rate = typeof wr === "number" ? wr : Number(wr ?? 0);
    const te = meta?.total_entries;
    const total_entries = typeof te === "number" ? te : Number(te ?? 0);
    return {
      ...s,
      total_entries: Number.isFinite(total_entries) ? total_entries : 0,
      color_identity: (meta?.color_identity as string[] | null) ?? null,
      avg_win_rate: Number.isFinite(avg_win_rate) ? avg_win_rate : 0,
    };
  });
}

async function getCoreStats() {
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
  const oneYearAgoIso = oneYearAgo.toISOString().split("T")[0];

  // Fetch candidates with > 60 entries (only ~200 rows)
  const { data: candidates, error: candidateErr } = await supabase
    .from("commander_stats")
    .select("commander_id, commander_name, total_entries, avg_win_rate, conversion_rate_top_cut, color_identity")
    .gt("total_entries", 60)
    .not("commander_name", "ilike", "unknown commander")
    .not("commander_name", "is", null)
    .neq("commander_name", "")
    .order("avg_win_rate", { ascending: false });

  if (candidateErr) {
    throw new Error(`Failed to fetch commander candidates: ${candidateErr.message}`);
  }

  const candidateIds = (candidates ?? []).map((c) => c.commander_id);

  // Check which candidates were active in the past year using monthly trends (fewer rows)
  // We chunk the IN clause to avoid URL length limits
  const activeIdsSet = new Set<string>();
  const CHUNK_SIZE = 100;
  for (let i = 0; i < candidateIds.length; i += CHUNK_SIZE) {
    const chunk = candidateIds.slice(i, i + CHUNK_SIZE);
    const { data: activeRows, error: activeErr } = await supabase
      .from("commander_monthly_trends")
      .select("commander_id")
      .in("commander_id", chunk)
      .gte("month_start_date", oneYearAgoIso);

    if (activeErr) {
      console.error(`Error fetching activity for chunk ${i}:`, activeErr.message);
      continue;
    }

    if (activeRows) {
      for (const row of activeRows) {
        activeIdsSet.add(row.commander_id);
      }
    }
  }

  const topWinRate = (candidates as TopCommander[] ?? [])
    .filter((row) => activeIdsSet.has(row.commander_id))
    .filter((row) => isKnownCommanderName(row.commander_name))
    .slice(0, 10);

  const topCommandersQuery = supabase
    .from("commander_stats")
    .select("commander_id, commander_name, total_entries, avg_win_rate, conversion_rate_top_cut, color_identity")
    .gt("total_entries", 20)
    .not("commander_name", "ilike", "unknown commander")
    .not("commander_name", "is", null)
    .neq("commander_name", "")
    .order("total_entries", { ascending: false })
    .limit(21);

  const { data: topCommandersData, error: topErr } = await topCommandersQuery;
  if (topErr) throw new Error(`Top commanders query failed: ${topErr.message}`);

  return {
    topCommanders: (topCommandersData as TopCommander[] ?? []).filter((row) =>
      isKnownCommanderName(row.commander_name)
    ),
    topWinRate,
  };
}

interface LeaderboardPlayer {
  player_id: string;
  topdeck_id: string;
  player_name: string;
  rank: number;
  topdeck_elo: number | null;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  active_commander: string | null;
  active_commander_decklist_url: string | null;
  latest_tournament_name: string | null;
  latest_tournament_date: string | null;
  latest_tournament_topdeck_tid: string | null;
}

async function getLeaderboardPreview(): Promise<LeaderboardPlayer[]> {
  try {
    const { data, error } = await supabase
      .from("global_elo_active_leaderboard")
      .select(
        "player_id, player_name, topdeck_id, topdeck_elo, topdeck_elo_rank, games_played, wins, draws, losses, last_game_date"
      )
      .eq("region_type", "global")
      .eq("region_key", "ALL")
      .not("topdeck_elo_rank", "is", null)
      .order("topdeck_elo_rank", { ascending: true })
      .limit(10);

    if (error) {
      console.error("Error fetching home leaderboard preview:", error);
      return [];
    }

    const leaderboardRows = ((data ?? []) as Array<{
      player_id: string;
      player_name: string;
      topdeck_id: string | null;
      topdeck_elo: number | null;
      topdeck_elo_rank: number | null;
      games_played: number;
      wins: number;
      draws: number;
      losses: number;
      last_game_date: string | null;
    }>).filter((row) => row.topdeck_id);

    const topdeckIds = leaderboardRows
      .map((row) => row.topdeck_id)
      .filter((value): value is string => Boolean(value));
    const [profileByTopdeckId, latestTournamentByPlayerId] = await Promise.all([
      fetchHomeLeaderboardProfiles(topdeckIds),
      fetchHomeLeaderboardLatestTournaments(leaderboardRows.map((row) => row.player_id)),
    ]);

    return leaderboardRows.map((row, index) => {
      const topdeckId = row.topdeck_id ?? "";
      const profile = profileByTopdeckId.get(topdeckId);
      const latestTournament = latestTournamentByPlayerId.get(row.player_id);
      return {
        player_id: row.player_id,
        topdeck_id: topdeckId,
        player_name: row.player_name,
        rank: row.topdeck_elo_rank ?? index + 1,
        topdeck_elo: row.topdeck_elo,
        games_played: row.games_played,
        wins: row.wins,
        draws: row.draws,
        losses: row.losses,
        last_game_date: row.last_game_date,
        active_commander: isKnownCommanderName(profile?.active_commander)
          ? profile?.active_commander ?? null
          : null,
        active_commander_decklist_url: profile?.latest_decklist_url ?? null,
        latest_tournament_name: latestTournament?.name ?? null,
        latest_tournament_date: latestTournament?.date ?? null,
        latest_tournament_topdeck_tid: latestTournament?.topdeck_tid ?? null,
      };
    });
  } catch (error) {
    console.error("Error fetching home leaderboard preview:", error);
    return [];
  }
}

async function fetchHomeLeaderboardProfiles(topdeckIds: string[]) {
  if (topdeckIds.length === 0) {
    return new Map<string, {
      active_commander: string | null;
      latest_decklist_url: string | null;
    }>();
  }

  const { data, error } = await supabase
    .from("player_commander_profiles")
    .select("topdeck_id, active_commander, latest_decklist_url")
    .in("topdeck_id", topdeckIds);

  if (error) {
    console.error("Error fetching home leaderboard profiles:", error);
    return new Map();
  }

  return new Map(
    ((data ?? []) as Array<{
      topdeck_id: string | null;
      active_commander: string | null;
      latest_decklist_url: string | null;
    }>)
      .filter((row) => row.topdeck_id)
      .map((row) => [row.topdeck_id as string, row])
  );
}

async function fetchHomeLeaderboardLatestTournaments(playerIds: string[]) {
  const uniquePlayerIds = Array.from(new Set(playerIds.filter(Boolean)));
  const latestByPlayerId = new Map<
    string,
    {
      name: string | null;
      date: string | null;
      topdeck_tid: string | null;
      tournament_id: string | null;
    }
  >();
  if (uniquePlayerIds.length === 0) return latestByPlayerId;

  for (const table of ["global_elo_game_event_log", "regional_elo_game_event_log"]) {
    const { data, error } = await supabase
      .from(table)
      .select("player_id, game_date, tournament_name, tournament_id")
      .in("player_id", uniquePlayerIds)
      .order("game_date", { ascending: false })
      .limit(250);

    if (error) continue;

    for (const row of (data ?? []) as Array<{
      player_id: string;
      game_date: string | null;
      tournament_name: string | null;
      tournament_id: string | null;
    }>) {
      if (latestByPlayerId.has(row.player_id)) continue;
      latestByPlayerId.set(row.player_id, {
        name: row.tournament_name ?? null,
        date: row.game_date ?? null,
        topdeck_tid: null,
        tournament_id: row.tournament_id ?? null,
      });
    }

    if (latestByPlayerId.size > 0) break;
  }

  const tournamentIds = Array.from(
    new Set(
      Array.from(latestByPlayerId.values())
        .map((row) => row.tournament_id)
        .filter((value): value is string => Boolean(value))
    )
  );
  if (tournamentIds.length === 0) return latestByPlayerId;

  const { data, error } = await supabase
    .from("tournaments")
    .select("id, name, start_date, topdeck_tid")
    .in("id", tournamentIds);

  if (error) return latestByPlayerId;

  const tournamentsById = new Map(
    ((data ?? []) as Array<{
      id: string;
      name: string | null;
      start_date: string | null;
      topdeck_tid: string | null;
    }>).map((row) => [row.id, row])
  );

  for (const latest of latestByPlayerId.values()) {
    if (!latest.tournament_id) continue;
    const tournament = tournamentsById.get(latest.tournament_id);
    if (!tournament) continue;
    latest.name = tournament.name ?? latest.name;
    latest.date = tournament.start_date ?? latest.date;
    latest.topdeck_tid = tournament.topdeck_tid ?? null;
  }

  return latestByPlayerId;
}

const getCachedHomeCoreStats = unstable_cache(
  getCoreStats,
  ["home-core-stats-v7"], // Updated cache key
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

const getCachedLeaderboardPreview = unstable_cache(
  getLeaderboardPreview,
  ["home-leaderboard-preview-v4"],
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

const getCachedHomeRisingCommanders = unstable_cache(
  getTopRisingCommandersByTwoWeekTrend,
  ["home-rising-commanders-v2"],
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

export default async function Home() {
  const [{ topCommanders, topWinRate }, topRisingCommanders, leaderboardPlayers] = await Promise.all([
    getCachedHomeCoreStats(),
    getCachedHomeRisingCommanders().catch((error) => {
      console.error("Home rising commanders cache refresh failed:", error);
      return [];
    }),
    getCachedLeaderboardPreview(),
  ]);
  const topThreePopular: TopCommander[] = topCommanders.slice(0, 3);
  const showTrendCards = topThreePopular.length > 0 || topRisingCommanders.length > 0;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-foreground md:text-4xl">tedh.gg</h1>
            </div>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <Link className="transition hover:text-foreground" href="/regional-elo">
                Leaderboard
              </Link>
              <Link className="transition hover:text-foreground" href="/commanders">
                Commanders
              </Link>
              <Link className="transition hover:text-foreground" href="/tournament-likelihood">
                Tournament Prep
              </Link>
              <Link className="transition hover:text-foreground" href="/about">
                Methodology
              </Link>
            </nav>
          </div>
        </header>

        <section className="mt-16 flex flex-col items-center gap-8 py-8 text-center border-b border-border/60">
          <div className="space-y-3">
            <h2 className="text-3xl font-semibold leading-tight text-foreground md:text-4xl">
              Competitive Intelligence for cEDH
            </h2>
            <p className="text-base text-muted-foreground">
              Player intelligence and competition research platform.
            </p>
          </div>
          <HomeSearchBar />
        </section>

        {leaderboardPlayers.length > 0 && (
          <section className="mt-12">
            <Card data-testid="global-leaderboard-card" className="border-primary/20 bg-primary/5">
              <CardHeader className="flex flex-row items-center justify-between pb-3 sm:pb-4">
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-base sm:text-lg truncate">Global Leaderboard</CardTitle>
                  <p className="text-[10px] sm:text-sm text-muted-foreground truncate">Active players ranked by TopDeck Elo</p>
                </div>
                <Button asChild variant="ghost" size="xs" className="shrink-0 border border-border/70 text-[10px] h-8 px-2 ml-2">
                  <Link href="/regional-elo">Full View</Link>
                </Button>
              </CardHeader>
              <CardContent className="px-2 sm:px-6">
                <div className="overflow-x-auto">
                  <Table data-testid="global-leaderboard-table">
                    <TableHeader>
                      <TableRow className="border-border/60 text-[10px] uppercase tracking-wider text-muted-foreground">
                        <TableHead className="py-2 px-1 w-8">#</TableHead>
                        <TableHead className="py-2 px-2">Player</TableHead>
                        <TableHead className="py-2 px-2 text-right">Elo</TableHead>
                        <TableHead className="py-2 px-2 hidden sm:table-cell">Commander</TableHead>
                        <TableHead className="py-2 px-2 hidden md:table-cell">Games</TableHead>
                        <TableHead className="py-2 px-2 hidden md:table-cell">W-L-D</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {leaderboardPlayers.map((player) => {
                        return (
                          <TableRow key={player.player_id} className="border-border/60">
                            <TableCell className="py-3 px-1 font-mono text-[10px] text-muted-foreground">
                              {player.rank}
                            </TableCell>
                            <TableCell className="py-3 px-2">
                              <Link
                                href={`/regional-elo/player/${player.topdeck_id}`}
                                className="font-medium text-foreground hover:text-primary text-xs sm:text-sm"
                              >
                                {player.player_name}
                              </Link>
                            </TableCell>
                            <TableCell className="py-3 px-2 text-right font-mono text-xs sm:text-sm font-semibold text-primary">
                              {player.topdeck_elo == null ? "—" : Math.round(player.topdeck_elo)}
                            </TableCell>
                            <TableCell className="py-3 px-2 max-w-[180px] text-[10px] text-muted-foreground hidden sm:table-cell">
                              {player.active_commander ? (
                                <span className="line-clamp-1">
                                  {player.active_commander}
                                </span>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                            <TableCell className="py-3 px-2 font-mono text-[10px] text-muted-foreground hidden md:table-cell">
                              {player.games_played.toLocaleString()}
                            </TableCell>
                            <TableCell className="py-3 px-2 font-mono text-[10px] text-muted-foreground hidden md:table-cell">
                              {player.wins}-{player.losses}-{player.draws}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </section>
        )}

        {showTrendCards ? (
          <section className="mt-12 grid gap-4 lg:grid-cols-2 lg:gap-6">
            {topThreePopular.length > 0 ? (
              <Card data-testid="top-popular-commanders" className="min-w-0">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Most Popular Commanders</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Ranked by total entries in large events.
                  </p>
                </CardHeader>
                <CardContent className="flex flex-col gap-2 p-2 sm:p-6 sm:gap-3">
                  {topThreePopular.map((commander, index) => (
                    <CommanderRow
                      key={commander.commander_id}
                      commander={commander}
                      rank={index + 1}
                    />
                  ))}
                </CardContent>
              </Card>
            ) : null}
            {topRisingCommanders.length > 0 ? (
              <Card data-testid="top-rising-commanders" className="min-w-0">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Rising Stars</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Biggest popularity gains in the past 2 weeks.
                  </p>
                </CardHeader>
                <CardContent className="flex flex-col gap-2 p-2 sm:p-6 sm:gap-3">
                  {topRisingCommanders.map((commander, index) => (
                    <RisingCommanderRow
                      key={commander.commander_id}
                      commander={commander}
                      rank={index + 1}
                    />
                  ))}
                </CardContent>
              </Card>
            ) : null}
          </section>
        ) : null}

        <section className="mt-12">
          <Card className="border-[hsl(var(--knd-amber))]/20 bg-[hsl(var(--knd-amber))]/5">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div className="min-w-0 flex-1">
                <CardTitle className="text-lg text-[hsl(var(--knd-amber))] truncate">Tournament Prep</CardTitle>
                <p className="text-[10px] sm:text-sm text-muted-foreground truncate">Estimate attendee likelihood and expected meta share for your next event</p>
              </div>
              <Button asChild variant="outline" size="sm" className="border-[hsl(var(--knd-amber))]/40 bg-card/60">
                <Link href="/tournament-likelihood">Run Simulator</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3 sm:gap-4">
                <div className="rounded-lg border border-border/60 bg-card/40 p-3 sm:p-4">
                  <h4 className="text-xs font-semibold text-foreground mb-1">Meta Simulation</h4>
                  <p className="text-[10px] text-muted-foreground">Simulate field compositions based on recent patterns.</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-card/40 p-3 sm:p-4">
                  <h4 className="text-xs font-semibold text-foreground mb-1">Archetype Coverage</h4>
                  <p className="text-[10px] text-muted-foreground">Identify deck types likely to appear in your region.</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-card/40 p-3 sm:p-4">
                  <h4 className="text-xs font-semibold text-foreground mb-1">Conversion Odds</h4>
                  <p className="text-[10px] text-muted-foreground">Calculate probability of reaching the top cut.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="mt-12 grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Field Performance</CardTitle>
              <p className="text-sm text-muted-foreground">Comprehensive statistics for top commanders</p>
            </CardHeader>
            <CardContent className="px-2 sm:px-6">
              <div className="overflow-x-auto">
                <Table className="knd-data-table">
                  <colgroup>
                    <col className="w-10" />
                    <col />
                    <col className="w-20 sm:w-24" />
                    <col className="w-16 sm:w-20" />
                    <col className="w-16 sm:w-20" />
                  </colgroup>
                  <TableHeader>
                    <TableRow className="border-border/60 text-[10px] uppercase tracking-wider text-muted-foreground">
                      <TableHead className="py-2 px-1 w-8">#</TableHead>
                      <TableHead className="py-2 px-2">Commander</TableHead>
                      <TableHead className="py-2 px-2 text-right hidden sm:table-cell">Entries</TableHead>
                      <TableHead className="py-2 px-2 text-right">Win%</TableHead>
                      <TableHead className="py-2 px-2 text-right">Cut%</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topCommanders.length > 0 ? (
                      topCommanders.map((commander, index) => (
                        <TableRow key={commander.commander_id} className="border-border/60">
                          <TableCell className="py-3 px-1 font-mono text-[10px] text-muted-foreground">#{index + 1}</TableCell>
                          <TableCell className="py-3 px-2">
                            <div className="flex items-center gap-2">
                              <div className="flex gap-0.5 shrink-0">
                                {commander.color_identity?.filter(Boolean).map((color: string) => (
                                  <ColorBadge key={color} color={color} isSmall />
                                ))}
                              </div>
                              <Link
                                className="knd-data-link text-xs sm:text-sm"
                                href={`/commanders/${commander.commander_id}`}
                              >
                                {normalizeDisplayString(commander.commander_name)}
                              </Link>
                            </div>
                          </TableCell>
                          <TableCell className="py-3 px-2 font-mono text-[10px] text-muted-foreground text-right hidden sm:table-cell">
                            {commander.total_entries}
                          </TableCell>
                          <TableCell className="py-3 px-2 font-mono text-xs sm:text-sm text-right">
                            {(() => {
                              const wr = typeof commander.avg_win_rate === "number" ? commander.avg_win_rate : parseFloat(commander.avg_win_rate || "0");
                              return (Number.isFinite(wr) ? wr * 100 : 0).toFixed(1);
                            })()}%
                          </TableCell>
                          <TableCell className="py-3 px-2 font-mono text-xs sm:text-sm text-right text-primary">
                            {(() => {
                              const conversion = typeof commander.conversion_rate_top_cut === "number" ? commander.conversion_rate_top_cut : parseFloat(commander.conversion_rate_top_cut || "0");
                              return (Number.isFinite(conversion) ? conversion * 100 : 0).toFixed(1);
                            })()}%
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow className="border-border/60">
                        <TableCell className="py-6 text-sm text-muted-foreground text-center" colSpan={5}>
                          No commander data available right now.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Win Rate Leaders</CardTitle>
              <p className="text-sm text-muted-foreground">Active last 12mo · 60+ entries</p>
            </CardHeader>
            <CardContent className="space-y-2 p-2 sm:p-6 sm:space-y-3">
              {topWinRate.length > 0 ? (
                topWinRate.map((commander, index) => (
                  <CommanderRow key={commander.commander_id} commander={commander} rank={index + 1} />
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No win-rate data available right now.</p>
              )}
              <Button asChild variant="ghost" className="w-full border border-border/70 mt-2 text-xs h-9">
                <Link href="/commanders">View All Commanders</Link>
              </Button>
            </CardContent>
          </Card>
        </section>

      </main>
    </div>
  );
}

function RisingCommanderRow({
  commander,
  rank,
}: {
  commander: RisingCommander;
  rank: number;
}) {
  const wrValue = typeof commander.avg_win_rate === "number" ? commander.avg_win_rate : parseFloat(commander.avg_win_rate as string);
  const winRate = (Number.isFinite(wrValue) ? wrValue * 100 : 0).toFixed(1);
  const isAboveExpected = wrValue > 0.25;

  return (
    <Link
      href={`/commanders/${commander.commander_id}`}
      className="flex w-full min-w-0 items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-2 py-2 sm:px-3 sm:py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <span className="shrink-0 font-mono text-[10px] text-muted-foreground w-4">#{rank}</span>
      <div className="flex shrink-0 flex-wrap gap-0.5 sm:gap-1">
        {commander.color_identity?.filter(Boolean).map((color: string) => (
          <ColorBadge key={color} color={color} isSmall />
        ))}
      </div>
      <div className="min-w-0 flex-1 ml-1">
        <p className="truncate text-xs sm:text-sm font-medium text-foreground">
          {normalizeDisplayString(commander.commander_name)}
        </p>
        <p className="truncate text-[10px] text-muted-foreground">
          {commander.recent_entries} entries · <span className={isAboveExpected ? "text-primary" : undefined}>{winRate}%</span> win
        </p>
      </div>
      <div className="shrink-0 text-right">
        <p className="font-mono text-xs sm:text-sm text-primary">+{(commander.meta_share_delta * 100).toFixed(1)}%</p>
        <p className="text-[9px] text-muted-foreground">meta Δ</p>
      </div>
    </Link>
  );
}
function CommanderRow({
  commander,
  rank,
}: {
  commander: TopCommander;
  rank: number;
}) {
  const wrValue = typeof commander.avg_win_rate === "number" ? commander.avg_win_rate : parseFloat(commander.avg_win_rate as string);
  const winRate = (Number.isFinite(wrValue) ? wrValue * 100 : 0).toFixed(1);
  const isAboveExpected = wrValue > 0.25;

  return (
    <Link
      href={`/commanders/${commander.commander_id}`}
      className="flex w-full min-w-0 items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-2 py-2 sm:px-3 sm:py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <span className="shrink-0 font-mono text-[10px] text-muted-foreground w-4">#{rank}</span>
      <div className="flex shrink-0 flex-wrap gap-0.5 sm:gap-1">
        {commander.color_identity?.filter(Boolean).map((color: string) => (
          <ColorBadge key={color} color={color} isSmall />
        ))}
      </div>
      <div className="min-w-0 flex-1 ml-1">
        <p className="truncate text-xs sm:text-sm font-medium text-foreground">
          {normalizeDisplayString(commander.commander_name)}
        </p>
        <p className="truncate text-[10px] text-muted-foreground">{commander.total_entries} entries</p>
      </div>
      <div className="shrink-0 text-right">
        <p className={`font-mono text-xs sm:text-sm ${isAboveExpected ? "text-primary" : "text-muted-foreground"}`}>
          {winRate}%
        </p>
        <p className="text-[9px] text-muted-foreground">win rate</p>
      </div>
    </Link>
  );
}

function ColorBadge({ color, isSmall }: { color: string; isSmall?: boolean }) {
  const colors: Record<string, string> = {
    W: "bg-amber-200/80 text-amber-950",
    U: "bg-sky-500/90 text-white",
    B: "bg-purple-900/90 text-purple-100",
    R: "bg-red-500/90 text-white",
    G: "bg-emerald-500/90 text-white",
  };

  return (
    <span
      className={`flex items-center justify-center rounded-full font-semibold ${
        isSmall ? "h-3.5 w-3.5 text-[8px]" : "h-5 w-5 text-[10px]"
      } ${colors[color] || "bg-slate-500 text-white"}`}
    >
      {color}
    </span>
  );
}
