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
  PlayerTournamentEntryRow,
  EntryRow,
} from "./page";
import { summarizePlayerLogs, type PlayerGameLog } from "./player-stats";

const PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS = 60 * 60 * 24;

// --- HELPERS ---

export function isKnownCommanderName(value: string | null | undefined) {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

export function firstRelation<T>(value: T | T[] | null) {
  return Array.isArray(value) ? value[0] ?? null : value;
}

export function sortAchievementsByFinish(rows: PlayerAchievementRow[]): PlayerAchievementRow[] {
  return [...rows].sort((a, b) => {
    if (a.finishRatio === null && b.finishRatio !== null) return 1;
    if (b.finishRatio === null && a.finishRatio !== null) return -1;
    if (a.finishRatio !== null && b.finishRatio !== null && a.finishRatio !== b.finishRatio) {
      return a.finishRatio - b.finishRatio;
    }
    if ((b.playerCount ?? 0) !== (a.playerCount ?? 0)) {
      return (b.playerCount ?? 0) - (a.playerCount ?? 0);
    }
    const dateCompare = (b.startDate ?? "").localeCompare(a.startDate ?? "");
    if (dateCompare !== 0) return dateCompare;
    return a.tournamentName.localeCompare(b.tournamentName);
  });
}

// --- DATA FETCHERS ---

export async function fetchEntries(playerId: string): Promise<EntryRow[]> {
  const SUPABASE_PAGE_SIZE = 1000;
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

export const fetchCachedPlayerCommanderProfile = unstable_cache(
  async (topdeckId: string) => {
    const { data: profileRow, error: profileError } = await supabase
      .from("player_commander_profiles")
      .select("active_commander, latest_decklist_url, latest_tournament_name, latest_tournament_date, latest_tournament_topdeck_tid")
      .eq("topdeck_id", topdeckId)
      .maybeSingle();

    if (profileError) return null;
    return profileRow as PlayerCommanderProfileRow | null;
  },
  ["regional-player-commander-profile-v1"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

async function fetchPlayerTournamentEntries(playerId: string): Promise<PlayerTournamentEntryRow[]> {
  const SUPABASE_PAGE_SIZE = 1000;
  const rows: PlayerTournamentEntryRow[] = [];
  for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
    const { data, error } = await supabase
      .from("tournament_entries")
      .select(
        "final_standing, wins, draws, losses, decklist_url, commanders(name), tournaments(name, start_date, player_count, topdeck_tid)"
      )
      .eq("player_id", playerId)
      .range(offset, offset + SUPABASE_PAGE_SIZE - 1);
    if (error) throw new Error(`Error fetching player tournament entries: ${error.message}`);
    rows.push(...((data as PlayerTournamentEntryRow[]) ?? []));
    if (!data || data.length < SUPABASE_PAGE_SIZE) break;
  }
  return rows;
}

export const fetchCachedPlayerAchievements = unstable_cache(
  async (playerId: string, topdeckId: string) => {
    const rows = await fetchPlayerTournamentEntries(playerId);
    return rows.map((row) => {
      const tournament = firstRelation(row.tournaments);
      const commander = firstRelation(row.commanders);
      return {
        tournamentName: tournament?.name ?? "Unknown tournament",
        tournamentUrl: tournament?.topdeck_tid ? `https://topdeck.gg/bracket/${tournament.topdeck_tid}` : null,
        startDate: tournament?.start_date ?? null,
        playerCount: tournament?.player_count ?? null,
        placement: row.final_standing ?? null,
        finishRatio: row.final_standing && tournament?.player_count ? row.final_standing / tournament.player_count : null,
        commanderName: isKnownCommanderName(commander?.name) ? commander?.name ?? null : null,
        decklistUrl: row.decklist_url || (tournament?.topdeck_tid ? `https://topdeck.gg/deck/${tournament.topdeck_tid}/${topdeckId}` : null),
        wins: Number(row.wins ?? 0),
        draws: Number(row.draws ?? 0),
        losses: Number(row.losses ?? 0),
        recordGames: Number(row.wins ?? 0) + Number(row.draws ?? 0) + Number(row.losses ?? 0),
      };
    }).sort((a, b) => (b.startDate ?? "").localeCompare(a.startDate ?? ""));
  },
  ["regional-player-achievements-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

export const fetchCachedPlayerCommanderUsageRows = unstable_cache(
  async (playerId: string, topdeckId: string, playerName: string) => {
    const rows = await fetchPlayerTournamentEntries(playerId);
    return rows.map((row) => {
      const tournament = firstRelation(row.tournaments);
      const commander = firstRelation(row.commanders);
      return {
        topdeck_id: topdeckId,
        player_name: playerName,
        commander_name: isKnownCommanderName(commander?.name) ? commander?.name ?? null : null,
        wins: row.wins,
        draws: row.draws,
        losses: row.losses,
        start_date: tournament?.start_date ?? null,
        player_count: tournament?.player_count ?? null,
        decklist_url: null,
        topdeck_decklist_url: tournament?.topdeck_tid ? `https://topdeck.gg/deck/${tournament.topdeck_tid}/${topdeckId}` : null,
        tournament_name: tournament?.name ?? null,
        tournament_topdeck_tid: tournament?.topdeck_tid ?? null,
      };
    }).filter((row) => row.commander_name && row.start_date);
  },
  ["regional-player-commander-usage-v3"],
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
  // Simplified version, in page.tsx there is a fallback to build from raw history.
  // We'll let PlayerProfileBody handle the complex logic if needed.
  return []; 
}

export const fetchCachedPlayerEventLogs = unstable_cache(
  async (playerId: string, regionFilter: string) => fetchPlayerEventLogs(playerId, regionFilter),
  ["regional-player-event-logs-v3"],
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
