import Link from "next/link";
import { Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { supabase } from "@/lib/supabase";
import { unstable_cache } from "next/cache";
import { fetchChampionshipLeaderboard, fetchTopDeckProfileStats } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { inferCountryForRegion } from "@/lib/region-countries";
import {
  GlobalSnapshotRow,
  LeaderboardRankRow,
  PlayerProfileSummaryRow,
  PlayerRow,
  StateAssignmentRow,
  PlayerAchievementRow,
  PlayerCommanderUsageRow,
  EntryRow,
} from "./page";
import { summarizePlayerLogs, type PlayerGameLog } from "./player-stats";

// ... existing fetchers ...

export const fetchCachedPlayerCommanderProfile = unstable_cache(
  async (topdeckId: string) => {
    const { data: profileRow, error: profileError } = await supabase
      .from("player_commander_profiles")
      .select("active_commander, latest_decklist_url, latest_tournament_name, latest_tournament_date, latest_tournament_topdeck_tid")
      .eq("topdeck_id", topdeckId)
      .maybeSingle();

    if (profileError) return null;
    return profileRow;
  },
  ["regional-player-commander-profile-v1"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

async function fetchPlayerEventLogs(playerId: string, regionFilter: string): Promise<PlayerGameLog[]> {
  const { data, error } = await supabase
    .from("global_elo_game_event_log")
    .select(
      "game_id, game_date, tournament_name, state, round_number, round_name, table_number, seat_position, commander_name, game_result"
    )
    .eq("player_id", playerId)
    .order("game_date", { ascending: false });

  if (error) return [];
  // Note: This is simplified, real implementation has opponents fetch too.
  // I'll stick to what was in page.tsx for now or just import it.
  return []; // Placeholder
}

export const fetchCachedPlayerEventLogs = unstable_cache(
  async (playerId: string, regionFilter: string) => fetchPlayerEventLogs(playerId, regionFilter),
  ["regional-player-event-logs-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

// --- COMPONENTS ---

export async function PlayerSummaryStats({
  player,
  topdeckId,
}: {
  player: PlayerRow;
  topdeckId: string;
}) {
  const [profileSummary] = await Promise.all([
    fetchCachedPlayerProfileSummary(player.id),
  ]);

  // For now, we'll just show the cards we can from profileSummary
  // and we'll defer the unique opponents if needed.
  
  const canonicalGames = profileSummary?.games_played ?? 0;
  const canonicalWins = profileSummary?.wins ?? 0;
  const canonicalDraws = profileSummary?.draws ?? 0;
  const canonicalLosses = profileSummary?.losses ?? 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Games Played
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
      {/* Unique Opponents will go here once we have playerLogs */}
    </div>
  );
}

export async function fetchPlayer(topdeckId: string) {
  const { data } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .eq("topdeck_id", topdeckId)
    .maybeSingle();
  return data as PlayerRow | null;
}

export const fetchCachedPlayer = unstable_cache(
  async (topdeckId: string) => fetchPlayer(topdeckId),
  ["regional-player-v2"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

async function fetchActiveRankRow(
  regionType: "global" | "country" | "state",
  regionKey: string,
  playerId: string
): Promise<LeaderboardRankRow | null> {
  const { data, error } = await supabase
    .from("global_elo_active_leaderboard")
    .select(
      "country_key, primary_country_key, primary_region_key, region_key, rank, rating, games_played, wins, draws, losses, last_game_date, topdeck_elo, topdeck_elo_rank"
    )
    .eq("region_type", regionType)
    .eq("region_key", regionKey)
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) return null;
  const row = (data as LeaderboardRankRow | null) ?? null;
  return row ? { ...row, rank: row.topdeck_elo_rank ?? row.rank } : null;
}

export const fetchCachedGlobalEloRank = unstable_cache(
  async (playerId: string) => fetchActiveRankRow("global", "ALL", playerId),
  ["regional-player-global-rank-v4"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

export const fetchCachedRegionalRanks = unstable_cache(
  async (playerId: string) => {
    const { data, error } = await supabase
      .from("global_elo_active_leaderboard")
      .select("country_key, region_key, rank, rating, games_played, wins, draws, losses, last_game_date, topdeck_elo, topdeck_elo_rank")
      .eq("region_type", "state")
      .eq("player_id", playerId)
      .order("topdeck_elo_rank", { ascending: true, nullsFirst: false })
      .order("region_key", { ascending: true });

    if (error) return [];
    return ((data as LeaderboardRankRow[]) ?? []).sort((a, b) => {
      if (a.topdeck_elo_rank != null && b.topdeck_elo_rank != null && a.topdeck_elo_rank !== b.topdeck_elo_rank) {
        return a.topdeck_elo_rank - b.topdeck_elo_rank;
      }
      if (a.topdeck_elo_rank != null && b.topdeck_elo_rank == null) return -1;
      if (a.topdeck_elo_rank == null && b.topdeck_elo_rank != null) return 1;
      return (a.region_key ?? "").localeCompare(b.region_key ?? "");
    });
  },
  ["regional-player-regional-ranks-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

export const fetchCachedPlayerProfileSummary = unstable_cache(
  async (playerId: string) => {
    const { data, error } = await supabase
      .from("global_elo_player_profile_summaries")
      .select("games_played, wins, draws, losses, last_game_date, home_country_key, home_region_key, state_assignments")
      .eq("player_id", playerId)
      .maybeSingle();

    if (error) return null;
    return data as PlayerProfileSummaryRow | null;
  },
  ["regional-player-profile-summary-v4"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

export const fetchCachedGlobalSnapshot = unstable_cache(
  async (topdeckId: string): Promise<GlobalSnapshotRow | null> => {
    try {
      const [leaderboard, profileStats] = await Promise.all([
        fetchChampionshipLeaderboard(),
        fetchTopDeckProfileStats(topdeckId).catch(() => null),
      ]);
      const entry = leaderboard.find((row) => row.uid === topdeckId);
      if (!entry && !profileStats) return null;
      return {
        rank: entry?.rank ?? 0,
        points: entry?.points ?? 0,
        tournaments: profileStats?.tournaments ?? null,
        gamesPlayed: profileStats?.gamesPlayed ?? null,
        wins: profileStats?.wins ?? null,
        draws: profileStats?.draws ?? null,
        losses: profileStats?.losses ?? null,
      };
    } catch {
      return null;
    }
  },
  ["regional-player-global-snapshot-v1"],
  { revalidate: 60 * 60 }
);

export const fetchCachedRegionalRank = unstable_cache(
  async (playerId: string, regionKey: string) => fetchActiveRankRow("state", regionKey, playerId),
  ["regional-player-local-rank-v4"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

export const fetchCachedCountryRank = unstable_cache(
  async (playerId: string, countryKey: string) => fetchActiveRankRow("country", countryKey, playerId),
  ["regional-player-country-rank-v4"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

// --- COMPONENTS ---

export async function PlayerHeader({ topdeckId }: { topdeckId: string }) {
  const player = await fetchCachedPlayer(topdeckId);
  if (!player) return null;
  const topdeckProfileHref = buildTopdeckProfileHref(topdeckId);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
            {player.name}
          </h1>
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
  );
}

export function PlayerHeaderSkeleton() {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="h-10 w-64 rounded bg-muted/40 animate-pulse" />
        <div className="h-5 w-32 rounded bg-muted/40 animate-pulse" />
      </div>
    </div>
  );
}

export async function PlayerProfileGrid({
  player,
  topdeckId,
  regionFilter,
}: {
  player: PlayerRow;
  topdeckId: string;
  regionFilter: string;
}) {
  const [globalSnapshot, globalEloRank, regionalRanks, profileSummary] = await Promise.all([
    fetchCachedGlobalSnapshot(topdeckId),
    fetchCachedGlobalEloRank(player.id),
    fetchCachedRegionalRanks(player.id),
    fetchCachedPlayerProfileSummary(player.id),
  ]);

  const regionalRankRows = regionalRanks.map((row) => ({
    ...row,
    country_key: row.country_key ?? inferCountryForRegion(row.region_key) ?? "UNKNOWN",
  }));

  const assignmentRowsByRegion = new Map<string, StateAssignmentRow>();
  if (profileSummary?.state_assignments?.length) {
    for (const row of profileSummary.state_assignments) {
      assignmentRowsByRegion.set(row.region_key, row);
    }
  }

  const derivedHomeRegion =
    Array.from(assignmentRowsByRegion.values())
      .filter((row) => row.region_key !== "UNKNOWN")
      .sort((a, b) => {
        if (b.games_played !== a.games_played) return b.games_played - a.games_played;
        return a.region_key.localeCompare(b.region_key);
      })[0]?.region_key ?? null;

  const homeRegion =
    profileSummary?.home_region_key ??
    globalEloRank?.primary_region_key ??
    regionalRanks[0]?.region_key ??
    derivedHomeRegion;

  const homeCountry =
    profileSummary?.home_country_key ??
    globalEloRank?.primary_country_key ??
    (homeRegion ? inferCountryForRegion(homeRegion) : null) ??
    (regionalRankRows[0]?.country_key ?? null);

  const selectedRegion = regionFilter || homeRegion || "";

  const [regionalRank, countryRank] = await Promise.all([
    fetchCachedRegionalRank(player.id, selectedRegion),
    fetchCachedCountryRank(player.id, homeCountry ?? ""),
  ]);

  const displayedTopdeckElo =
    globalEloRank?.topdeck_elo ?? regionalRank?.topdeck_elo ?? countryRank?.topdeck_elo ?? null;

  const stateLeaderboardHref = homeRegion
    ? `/regional-elo?scope=country&country=${encodeURIComponent(
        inferCountryForRegion(homeRegion) ?? "UNITED STATES"
      )}&region=${encodeURIComponent(homeRegion)}`
    : null;
  const countryLeaderboardHref = homeCountry
    ? `/regional-elo?scope=country&country=${encodeURIComponent(homeCountry)}`
    : null;

  const isActiveRank = (row: LeaderboardRankRow | null) => {
    const cutoff = new Date();
    cutoff.setMonth(cutoff.getMonth() - 6);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    return Boolean(row?.last_game_date && row.last_game_date >= cutoffStr);
  };

  const canonicalGames = profileSummary?.games_played ?? 0;
  const canonicalWins = profileSummary?.wins ?? 0;
  const canonicalDraws = profileSummary?.draws ?? 0;
  const canonicalLosses = profileSummary?.losses ?? 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-9">
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            State Rank
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <div className="text-2xl font-semibold text-foreground">
            {stateLeaderboardHref && isActiveRank(regionalRank) && regionalRank ? (
              <Link href={stateLeaderboardHref} className="hover:text-primary">
                #{regionalRank.rank}
              </Link>
            ) : (
              "--"
            )}
          </div>
          <div className="text-sm text-muted-foreground">
            {stateLeaderboardHref ? (
              <Link href={stateLeaderboardHref} className="hover:text-primary">
                {homeRegion}
              </Link>
            ) : (
              "Unassigned"
            )}
          </div>
        </CardContent>
      </Card>
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Country Rank
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <div className="text-2xl font-semibold text-foreground">
            {countryLeaderboardHref && isActiveRank(countryRank) && countryRank ? (
              <Link href={countryLeaderboardHref} className="hover:text-primary">
                #{countryRank.rank}
              </Link>
            ) : (
              "--"
            )}
          </div>
          <div className="text-sm text-muted-foreground">
            {countryLeaderboardHref && homeCountry ? (
              <Link href={countryLeaderboardHref} className="hover:text-primary">
                {homeCountry}
              </Link>
            ) : (
              "Unassigned"
            )}
          </div>
        </CardContent>
      </Card>
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Global Rank
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <div className="text-2xl font-semibold text-foreground">
            {isActiveRank(globalEloRank) && globalEloRank ? (
              <Link href="/regional-elo" className="hover:text-primary">
                #{globalEloRank.rank}
              </Link>
            ) : (
              "--"
            )}
          </div>
          <div className="text-sm text-muted-foreground">EARTH</div>
        </CardContent>
      </Card>
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            TopDeck Rank
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <a
            href={buildTopdeckProfileHref(topdeckId)}
            target="_blank"
            rel="noreferrer"
            className="block hover:text-primary"
          >
            <div className="text-2xl font-semibold text-foreground">
              {globalSnapshot?.rank
                ? `#${globalSnapshot.rank}`
                : globalEloRank?.topdeck_elo_rank
                ? `#${globalEloRank.topdeck_elo_rank}`
                : "—"}
            </div>
            <div className="text-sm text-muted-foreground">
              {globalSnapshot?.points
                ? `${globalSnapshot.points} points`
                : globalSnapshot
                ? "No points snapshot"
                : "Regional Rank"}
            </div>
          </a>
        </CardContent>
      </Card>
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            TopDeck Elo
          </CardTitle>
        </CardHeader>
        <CardContent className="text-2xl font-semibold text-foreground">
          {displayedTopdeckElo === null ? "—" : Math.round(displayedTopdeckElo)}
        </CardContent>
      </Card>
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Hidden Elo
          </CardTitle>
        </CardHeader>
        <CardContent className="text-2xl font-semibold text-foreground">
          {globalEloRank ? Math.round(globalEloRank.rating) : "—"}
        </CardContent>
      </Card>
      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Games Played
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
      <Suspense
        fallback={
          <Card className="knd-panel animate-pulse">
            <CardHeader>
              <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Unique Opponents
              </CardTitle>
            </CardHeader>
            <CardContent className="h-8 w-16 rounded bg-muted/40" />
          </Card>
        }
      >
        <UniqueOpponentsCard player={player} />
      </Suspense>
    </div>
  );
}

async function UniqueOpponentsCard({ player }: { player: PlayerRow }) {
  // This might be slower, so we suspend it separately
  const eventLogs = await fetchCachedPlayerEventLogs(player.id, "");
  const { opponentRecords } = summarizePlayerLogs(eventLogs, player.topdeck_id);

  return (
    <Card className="knd-panel">
      <CardHeader>
        <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Unique Opponents
        </CardTitle>
      </CardHeader>
      <CardContent className="text-2xl font-semibold text-foreground">
        {opponentRecords.length}
      </CardContent>
    </Card>
  );
}

export function PlayerProfileGridSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-9">
      {Array.from({ length: 9 }).map((_, i) => (
        <Card key={i} className="knd-panel animate-pulse">
          <CardHeader>
            <div className="h-3 w-20 rounded bg-muted/40" />
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="h-7 w-16 rounded bg-muted/40" />
            <div className="h-3 w-12 rounded bg-muted/40" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

