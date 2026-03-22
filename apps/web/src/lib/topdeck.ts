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
    username?: string | null;
    standing: number;
    points: number;
    winRate: number;
    opponentWinRate: number;
  }>;
  rounds: unknown[];
};

const CHAMPIONSHIP_LEADERBOARD_URL =
  "https://topdeck.gg/championship-series-2026/leaderboard";

export function extractTournamentSlug(input: string): string {
  const value = input.trim();
  if (!value) return "";

  try {
    const normalized = value.startsWith("http://") || value.startsWith("https://")
      ? value
      : `https://${value}`;
    const url = new URL(normalized);
    const segments = url.pathname.split("/").filter(Boolean);
    const knownPrefixes = new Set(["event", "bracket", "tournament", "tournaments"]);
    const slug = segments.length >= 2 && knownPrefixes.has(segments[0]) ? segments[1] : segments.at(-1);
    return slug?.trim() ?? "";
  } catch {
    const compact = value.replace(/^https?:\/\//, "").replace(/^topdeck\.gg\//, "");
    const segments = compact.split("/").filter(Boolean);
    if (segments.length === 0) return "";
    const knownPrefixes = new Set(["event", "bracket", "tournament", "tournaments"]);
    return segments.length >= 2 && knownPrefixes.has(segments[0]) ? segments[1] : segments.at(-1) ?? "";
  }
}

export async function fetchChampionshipLeaderboard(): Promise<TopDeckLeaderboardEntry[]> {
  const res = await fetch(CHAMPIONSHIP_LEADERBOARD_URL, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`TopDeck leaderboard fetch failed (${res.status})`);
  }
  const html = await res.text();
  const match = html.match(/const Leaderboard = (\[[\s\S]*?\]);/);
  if (!match) {
    throw new Error("TopDeck leaderboard payload not found in HTML");
  }
  return JSON.parse(match[1]) as TopDeckLeaderboardEntry[];
}

export async function fetchTournamentBySlug(slug: string): Promise<TopDeckTournamentResponse> {
  const apiKey = process.env.TOPDECK_API_KEY;
  if (apiKey) {
    const res = await fetch(`https://topdeck.gg/api/v2/tournaments/${slug}`.trim(), {
      headers: {
        Authorization: apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(
        `TopDeck API failed (${res.status}). TOPDECK_API_KEY is set, so fallback was skipped.`
      );
    }
    return (await res.json()) as TopDeckTournamentResponse;
  }

  const [bracketResponse, playersResponse] = await Promise.all([
    fetch(`https://topdeck.gg/bracket/${slug}`.trim(), { cache: "no-store" }),
    fetch(`https://topdeck.gg/PublicPData/${slug}`.trim(), { cache: "no-store" }),
  ]);

  if (!bracketResponse.ok || !playersResponse.ok) {
    const status = `${bracketResponse.status}/${playersResponse.status}`;
    throw new Error(`TopDeck tournament fetch failed (${status})`);
  }

  const [html, playersJson] = await Promise.all([bracketResponse.text(), playersResponse.json()]);
  const titleMatch = html.match(/<title>(.*?)<\/title>/i);
  const title = (titleMatch?.[1] ?? slug).replace(/\s*-\s*Tournament Standings\s*$/i, "").trim();
  const players = Object.values(playersJson as Record<string, {
    name?: string | null;
    uid?: string | null;
    username?: string | null;
  }>);

  return {
    data: {
      name: title || slug,
      game: "Magic: The Gathering",
      format: "EDH",
      startDate: "",
    },
    standings: players
      .map((player, index) => ({
        name: player?.name ?? "Unknown",
        id: player?.uid ?? "",
        username: player?.username ?? null,
        standing: index + 1,
        points: 0,
        winRate: 0,
        opponentWinRate: 0,
      }))
      .filter((row) => row.id.length > 0),
    rounds: [],
  };
}
