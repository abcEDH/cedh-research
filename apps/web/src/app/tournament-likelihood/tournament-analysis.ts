import "server-only";
import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";
import { fetchTournamentBySlug } from "@/lib/topdeck";
import { attachLatestDecklistUrls, buildProfiles, COMMANDER_FALLBACK_LOOKBACK_MONTHS,
  getCommanderDecklistRows, getCommanderUsageRows, lookbackStartDate, selectCommanderForecastRows } from "@/lib/meta-prep";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";

function readStartTimestamp(startDate: string | number | null | undefined) {
  if (typeof startDate === "number") return startDate * 1000;
  if (!startDate) return null;
  const timestamp = Date.parse(startDate);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export type TournamentStanding = {
  name: string;
  id: string;
  username?: string | null;
  standing: number;
  points: number;
  winRate: number;
  opponentWinRate: number;
  wins: number;
  draws: number;
  losses: number;
  actualDeckCommander: string | null;
  actualDecklistUrl: string | null;
};

export type EloRow = {
  topdeck_id: string | null;
  player_name: string;
  rating: number | null;
  hidden_rating?: number;
  topdeck_elo?: number | null;
  games_played: number;
  region_key: string;
};

type RegionalLeaderboardQueryRow = {
  topdeck_id: string | null;
  player_name: string;
  rating: number;
  topdeck_elo: number | null;
  games_played: number;
  primary_region_key: string | null;
  region_key: string;
  rank: number;
};

type PrecomputedCommanderPrediction = {
  commander: string;
  entries: number;
  prediction_score: number;
  prediction_share: number;
  latest_date: string | null;
  latest_decklist_url: string | null;
};

type PrecomputedCommanderProfileRow = {
  topdeck_id: string | null;
  player_name: string | null;
  total_entries: number;
  commander_predictions: PrecomputedCommanderPrediction[] | null;
};

function chunkArray<T>(values: T[], chunkSize = 250) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += chunkSize) {
    chunks.push(values.slice(index, index + chunkSize));
  }
  return chunks;
}







export async function fetchBestEloRows(topdeckIds: string[]): Promise<EloRow[]> {
  if (topdeckIds.length === 0) return [];

  // Query global_elo_active_leaderboard for player ratings
  // The rating column contains our calculated Elo for each player
  // The topdeck_elo column contains the official TopDeck Elo
  const { data, error } = await supabase
    .from("global_elo_active_leaderboard")
    .select("topdeck_id, player_name, rating, topdeck_elo, games_played, primary_region_key, region_key, rank")
    .in("topdeck_id", topdeckIds)
    .eq("region_type", "global")
    .eq("region_key", "ALL");

  if (error) {
    throw new Error(`Error fetching Elo rows: ${error.message}`);
  }

  const rowsByTopdeckId = new Map(
    ((data ?? []) as RegionalLeaderboardQueryRow[])
      .filter((row) => row.topdeck_id)
      .map((row) => [row.topdeck_id as string, row])
  );

  return Array.from(new Set(topdeckIds))
    .map((topdeckId) => {
      const row = rowsByTopdeckId.get(topdeckId);
      return {
        topdeck_id: topdeckId,
        player_name: row?.player_name ?? "",
        rating: row?.rating ?? null,
        hidden_rating: undefined,
        topdeck_elo: row?.topdeck_elo ?? null,
        games_played: row?.games_played ?? 0,
        region_key: row?.primary_region_key ?? row?.region_key ?? "",
      };
    })
    .sort((a, b) => (b.rating ?? -Infinity) - (a.rating ?? -Infinity));
}

async function fetchLatestPlayerNames(topdeckIds: string[]): Promise<Map<string, string>> {
  const names = new Map<string, string>();
  const uniqueTopdeckIds = Array.from(new Set(topdeckIds.filter(Boolean)));
  for (const topdeckIdChunk of chunkArray(uniqueTopdeckIds)) {
    const { data, error } = await supabase
      .from("players")
      .select("topdeck_id, name")
      .in("topdeck_id", topdeckIdChunk);

    if (error) {
      continue;
    }

    for (const row of (data ?? []) as Array<{ topdeck_id: string | null; name: string | null }>) {
      if (row.topdeck_id && row.name) {
        names.set(row.topdeck_id, row.name);
      }
    }
  }
  return names;
}

function applyLatestPlayerNamesToProfiles(
  profiles: { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] },
  latestPlayerNames: Map<string, string>
) {
  return {
    ...profiles,
    players: profiles.players.map((profile) => ({
      ...profile,
      playerName: latestPlayerNames.get(profile.topdeckId) ?? profile.playerName,
    })),
  };
}

async function fetchPrecomputedProfiles(
  topdeckIds: string[]
): Promise<{ players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } | null> {
  if (topdeckIds.length === 0) return { players: [], metaShare: [] };

  const { data, error } = await supabase
    .from("player_commander_profiles")
    .select("topdeck_id, player_name, total_entries, commander_predictions")
    .in("topdeck_id", topdeckIds);

  if (error) {
    return null;
  }

  const rowsByTopdeckId = new Map(
    ((data ?? []) as PrecomputedCommanderProfileRow[])
      .filter((row) => row.topdeck_id)
      .map((row) => [row.topdeck_id as string, row])
  );
  if (rowsByTopdeckId.size === 0) return null;

  const metaTotals = new Map<string, number>();
  const players = topdeckIds.map((topdeckId) => {
    const row = rowsByTopdeckId.get(topdeckId);
    const commanders = (row?.commander_predictions ?? []).slice(0, 3).map((commander) => {
      metaTotals.set(
        commander.commander,
        (metaTotals.get(commander.commander) ?? 0) + commander.prediction_share
      );
      return {
        commander: commander.commander,
        entries: commander.entries,
        share: commander.prediction_share,
        weightedShare: commander.prediction_share,
        predictionShare: commander.prediction_share,
        predictionScore: commander.prediction_score,
        latestDate: commander.latest_date,
        latestDecklistUrl: commander.latest_decklist_url,
        latestTopdeckDecklistUrl: null,
      };
    });

    return {
      topdeckId,
      playerName: row?.player_name ?? "Unknown",
      totalEntries: row?.total_entries ?? 0,
      commanders,
    };
  });
  const totalMeta = Array.from(metaTotals.values()).reduce((sum, value) => sum + value, 0);
  const metaShare = Array.from(metaTotals.entries())
    .map(([commander, entries]) => ({
      commander,
      entries,
      share: totalMeta ? entries / totalMeta : 0,
    }))
    .sort((a, b) => b.entries - a.entries)
    .slice(0, 15);

  return { players, metaShare };
}

const getCachedCommanderForecasts = unstable_cache(
  async (topdeckIds: string[], startTimestamp: number | null, lookbackMonths: number, anchorToStartDate: boolean) => {
    const now = Date.now();
    const anchorTimestamp = anchorToStartDate && startTimestamp ? startTimestamp : now;
    const referenceDate = new Date(anchorTimestamp);
    const lookbackStart = lookbackStartDate(lookbackMonths, referenceDate);
    const fallbackLookbackStart = lookbackStartDate(COMMANDER_FALLBACK_LOOKBACK_MONTHS, referenceDate);
    const lookbackEnd = anchorToStartDate ? referenceDate.toISOString().slice(0, 10) : undefined;
    const [precomputedProfiles, decklistRows, latestPlayerNames] = await Promise.all([
      anchorToStartDate ? Promise.resolve(null) : fetchPrecomputedProfiles(topdeckIds),
      getCommanderDecklistRows(topdeckIds, lookbackEnd),
      fetchLatestPlayerNames(topdeckIds),
    ]);
    if (precomputedProfiles) {
      return {
        latestPlayerNames: Array.from(latestPlayerNames),
        profiles: applyLatestPlayerNamesToProfiles(
          attachLatestDecklistUrls(precomputedProfiles, decklistRows),
          latestPlayerNames
        ),
      };
    }
    const primaryUsageRows = await getCommanderUsageRows(topdeckIds, lookbackStart, lookbackEnd);
    const twelveMonthEntryCounts = new Map<string, number>();
    for (const row of primaryUsageRows) {
      if (!row.topdeck_id || !row.commander_name) continue;
      twelveMonthEntryCounts.set(row.topdeck_id, (twelveMonthEntryCounts.get(row.topdeck_id) ?? 0) + 1);
    }
    const sparseTopdeckIds = topdeckIds.filter((topdeckId) => (twelveMonthEntryCounts.get(topdeckId) ?? 0) < 2);
    const fallbackUsageRows = sparseTopdeckIds.length
      ? await getCommanderUsageRows(sparseTopdeckIds, fallbackLookbackStart, lookbackStart)
      : [];
    for (const row of fallbackUsageRows) {
      if (!row.topdeck_id || !row.commander_name) continue;
      twelveMonthEntryCounts.set(row.topdeck_id, (twelveMonthEntryCounts.get(row.topdeck_id) ?? 0) + 1);
    }
    const noTwelveMonthHistoryTopdeckIds = topdeckIds.filter(
      (topdeckId) => (twelveMonthEntryCounts.get(topdeckId) ?? 0) === 0
    );
    const lastKnownFallbackRows = noTwelveMonthHistoryTopdeckIds.length
      ? await getCommanderUsageRows(noTwelveMonthHistoryTopdeckIds, "1900-01-01", fallbackLookbackStart)
      : [];
    const usageRows = selectCommanderForecastRows(
      topdeckIds,
      [...primaryUsageRows, ...fallbackUsageRows, ...lastKnownFallbackRows],
      referenceDate
    );
    const profiles = buildProfiles(topdeckIds, usageRows, 3, referenceDate.toISOString());

    return {
      latestPlayerNames: Array.from(latestPlayerNames),
      profiles: applyLatestPlayerNamesToProfiles(
        attachLatestDecklistUrls(profiles, decklistRows),
        latestPlayerNames
      ),
    };
  },
  ["tournament-commander-forecasts-v1"],
  { revalidate: 60 * 15 }
);


// Standings and round results are always fetched outside the historical forecast cache.
export async function getTournamentAnalysis(slug: string, lookbackMonths: number) {
  const response = await fetchTournamentBySlug(slug);
  const standings = response.standings as TournamentStanding[];
  const topdeckIds = Array.from(new Set(standings.map((row) => row.id).filter(Boolean))).sort();
  const startTimestamp = readStartTimestamp(response.data.startDate);
  const forecast = await getCachedCommanderForecasts(topdeckIds, startTimestamp, lookbackMonths, Boolean(startTimestamp && Date.now() >= startTimestamp));
  const latestNames = new Map(forecast.latestPlayerNames);
  return {
    tournament: response.data,
    standings: standings.map((standing) => ({ ...standing, name: latestNames.get(standing.id) ?? standing.name })),
    profiles: forecast.profiles,
    hasRounds: response.rounds.length > 0,
    standingsAvailable: response.standingsAvailable,
    updatedAt: new Date().toISOString(),
  };
}
