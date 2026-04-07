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
    startDate: string | number;
  };
  standings: Array<{
    name: string;
    id: string;
    username?: string | null;
    standing: number;
    points: number;
    winRate?: number | null;
    opponentWinRate?: number | null;
    successRate?: number | null;
    opponentSuccessRate?: number | null;
    wins: number;
    draws: number;
    losses: number;
    decklist?: string | null;
    deckObj?: TopDeckDeckObject | null;
    actualDeckCommander: string | null;
    actualDecklistUrl: string | null;
  }>;
  rounds: TopDeckRound[];
};

type TopDeckDeckObject = {
  Commanders?: Record<string, unknown>;
};

type TopDeckRound = {
  tables?: Array<{
    status?: string | null;
    winner_id?: string | null;
    players?: Array<{
      id?: string | null;
    }>;
  }>;
};

const CHAMPIONSHIP_LEADERBOARD_URL =
  "https://topdeck.gg/championship-series-2026/leaderboard";

async function fetchTopdeckWithRetry(url: string, apiKey: string, attempts = 3) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const res = await fetch(url, {
      headers: { Authorization: apiKey },
      cache: "no-store",
    });

    if (res.ok) return res;

    if (res.status !== 429 || attempt === attempts - 1) {
      throw new Error(`TopDeck API failed (${res.status}). TOPDECK_API_KEY is set, so fallback was skipped.`);
    }

    const retryAfterHeader = res.headers.get("Retry-After");
    const retryAfterSeconds = Number(retryAfterHeader);
    const waitMs = Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0
      ? retryAfterSeconds * 1000
      : 5000 * (attempt + 1);
    await new Promise((resolve) => setTimeout(resolve, waitMs));
  }

  throw new Error("TopDeck API retry budget exhausted.");
}

function normalizeStandingRates<T extends TopDeckTournamentResponse>(response: T): T {
  return {
    ...response,
    standings: response.standings.map((standing) => ({
      ...standing,
      winRate: standing.winRate ?? standing.successRate ?? 0,
      opponentWinRate: standing.opponentWinRate ?? standing.opponentSuccessRate ?? 0,
    })),
  };
}

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

function withTournamentRecords(response: TopDeckTournamentResponse): TopDeckTournamentResponse {
  const records = new Map<string, { wins: number; draws: number; losses: number }>();

  for (const round of response.rounds ?? []) {
    for (const table of round.tables ?? []) {
      if (table.status && table.status !== "Completed") continue;
      const playerIds = (table.players ?? [])
        .map((player) => player.id)
        .filter((id): id is string => Boolean(id));
      if (playerIds.length === 0) continue;

      for (const playerId of playerIds) {
        const record = records.get(playerId) ?? { wins: 0, draws: 0, losses: 0 };
        if (!table.winner_id) {
          record.draws += 1;
        } else if (table.winner_id === playerId) {
          record.wins += 1;
        } else {
          record.losses += 1;
        }
        records.set(playerId, record);
      }
    }
  }

  return {
    ...response,
    standings: response.standings.map((standing) => ({
      ...standing,
      ...(records.get(standing.id) ?? { wins: 0, draws: 0, losses: 0 }),
    })),
  };
}

function extractCommanderNameFromDecklist(value: string | null | undefined) {
  if (!value || !value.includes("~~Commanders~~")) return null;
  const normalized = value.replace(/\\n/g, "\n");
  const [, commanderBlock] = normalized.split("~~Commanders~~");
  const [commanders] = commanderBlock.split(/~~\w+~~|\n\s*\n/);
  const commanderNames = commanders
    .split("\n")
    .map((line) => line.trim().replace(/^\d+x?\s+/i, ""))
    .filter(Boolean);

  return commanderNames.length ? commanderNames.join(" / ") : null;
}

function getCommanderName(standing: TopDeckTournamentResponse["standings"][number]) {
  const deckObjectCommanders = standing.deckObj?.Commanders ? Object.keys(standing.deckObj.Commanders) : [];
  if (deckObjectCommanders.length > 0) return deckObjectCommanders.join(" / ");
  return extractCommanderNameFromDecklist(standing.decklist);
}

function buildTopdeckDecklistUrl(tournamentSlug: string, topdeckId: string) {
  return `https://topdeck.gg/deck/${tournamentSlug}/${topdeckId}`;
}

function withActualDecklists(response: TopDeckTournamentResponse, slug: string): TopDeckTournamentResponse {
  return {
    ...response,
    standings: response.standings.map((standing) => {
      const { decklist, deckObj, ...rest } = standing;
      return {
        ...rest,
        actualDeckCommander: getCommanderName(standing),
        actualDecklistUrl: decklist || deckObj ? buildTopdeckDecklistUrl(slug, standing.id) : null,
      };
    }),
  };
}

export async function fetchTournamentBySlug(slug: string): Promise<TopDeckTournamentResponse> {
  const apiKey = process.env.TOPDECK_API_KEY;
  if (apiKey) {
    const res = await fetchTopdeckWithRetry(`https://topdeck.gg/api/v2/tournaments/${slug}`.trim(), apiKey);
    return withActualDecklists(
      withTournamentRecords(normalizeStandingRates((await res.json()) as TopDeckTournamentResponse)),
      slug
    );
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
    decklist?: string | null;
  }>);

  return withActualDecklists(withTournamentRecords({
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
        successRate: null,
        opponentSuccessRate: null,
        wins: 0,
        draws: 0,
        losses: 0,
        decklist: player?.decklist ?? null,
        deckObj: null,
        actualDeckCommander: null,
        actualDecklistUrl: null,
      }))
      .filter((row) => row.id.length > 0),
    rounds: [],
  }), slug);
}
