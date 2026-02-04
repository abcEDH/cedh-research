import "server-only";

export type TopDeckLeaderboardEntry = {
  name: string;
  username?: string | null;
  profileImage?: string | null;
  uid: string;
  points: number;
  rank: number;
  twitter?: string | null;
  youtube?: string | null;
};

type TopDeckTournamentResponse = {
  data: {
    name: string;
    game: string;
    format: string;
    startDate: string;
  };
  standings: Array<{
    name: string;
    id: string;
    standing: number;
    points: number;
    winRate: number;
    opponentWinRate: number;
  }>;
  rounds: any[];
};

const CHAMPIONSHIP_LEADERBOARD_URL =
  "https://topdeck.gg/championship-series-2026/leaderboard";

export async function fetchChampionshipLeaderboard(): Promise<TopDeckLeaderboardEntry[]> {
  const res = await fetch(CHAMPIONSHIP_LEADERBOARD_URL, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`TopDeck leaderboard fetch failed (${res.status})`);
  }
  const html = await res.text();
  const match = html.match(/const Leaderboard = (\[.*?\]);/s);
  if (!match) {
    throw new Error("TopDeck leaderboard payload not found in HTML");
  }
  return JSON.parse(match[1]) as TopDeckLeaderboardEntry[];
}

export async function fetchTournamentBySlug(slug: string): Promise<TopDeckTournamentResponse> {
  const apiKey = process.env.TOPDECK_API_KEY;
  if (!apiKey) {
    throw new Error("TOPDECK_API_KEY is not set");
  }
  const res = await fetch(`https://topdeck.gg/api/v2/tournaments/${slug}`.trim(), {
    headers: {
      Authorization: apiKey,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`TopDeck tournament fetch failed (${res.status})`);
  }
  return (await res.json()) as TopDeckTournamentResponse;
}
