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

export type TopDeckProfileStats = {
  tournaments: number;
  gamesPlayed: number;
  wins: number;
  draws: number;
  losses: number;
};

type TopDeckProfileStatsResponse = {
  yearlyStats?: Record<
    string,
    Record<
      string,
      | {
          totalTournaments?: number | null;
          wins?: number | null;
          draws?: number | null;
          losses?: number | null;
        }
      | undefined
    >
  >;
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

export type TournamentStructureSource = "event_page" | "fallback";

export type TournamentStructureDefaults = {
  swissRounds: number;
  topCut: number;
  source: TournamentStructureSource;
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
const TOPDECK_FIRESTORE_PROJECT_ID = "eminence-1b40b";
const TOPDECK_FIRESTORE_API_KEY = "AIzaSyBISF4HIfUsepAAqqYHte2NE_L8eaT6iwI";
const FALLBACK_SWISS_ROUNDS = 6;
const FALLBACK_TOP_CUT = 16;

type FirestoreFieldValue = {
  integerValue?: string;
  doubleValue?: number;
  stringValue?: string;
  booleanValue?: boolean;
  nullValue?: null;
};

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
    const retryAfterMs = parseRetryAfterHeader(retryAfterHeader);
    const waitMs = retryAfterMs !== null
      ? retryAfterMs
      : 5000 * (attempt + 1);
    await new Promise((resolve) => setTimeout(resolve, waitMs));
  }

  throw new Error("TopDeck API retry budget exhausted.");
}

function parseRetryAfterHeader(value: string | null): number | null {
  if (!value) return null;

  const retryAfterSeconds = Number(value);
  if (Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0) {
    return retryAfterSeconds * 1000;
  }

  const retryAfterDate = Date.parse(value);
  if (Number.isFinite(retryAfterDate)) {
    return Math.max(retryAfterDate - Date.now(), 0);
  }

  return null;
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

function decodeHtmlEntities(value: string) {
  return value
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, "\"")
    .replace(/&#39;/gi, "'");
}

function normalizeEventPageText(html: string) {
  return decodeHtmlEntities(
    html
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
  );
}

function firstPositiveIntegerMatch(text: string, patterns: RegExp[]) {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    const candidate = Number(match?.[1]);
    if (Number.isInteger(candidate) && candidate > 0) {
      return candidate;
    }
  }
  return null;
}

export function inferTournamentStructureFromText(textOrHtml: string): TournamentStructureDefaults | null {
  const text = normalizeEventPageText(textOrHtml);
  const swissRounds = firstPositiveIntegerMatch(text, [
    /\b(\d{1,2})\s+Rounds?\s+of\s+Swiss\b/i,
    /\b(\d{1,2})\s+Swiss\s+Rounds?\b/i,
    /\b(\d{1,2})\s+Round(?:s)?\s+Swiss\b/i,
    /\bSwiss\s*[:\-]\s*(\d{1,2})\s+Rounds?\b/i,
    /\bSwiss[^0-9]{0,30}(\d{1,2})\s+Rounds?\b/i,
  ]);
  const topCut = firstPositiveIntegerMatch(text, [
    /\bCut\s+to\s+Top\s*(\d{1,3})\b/i,
    /\bCut\s*[:\-]\s*Top\s*(\d{1,3})\b/i,
    /\bTop\s*(\d{1,3})\s+Cut\b/i,
    /\bTop\s*(\d{1,3})\s+Playoff\b/i,
  ]);

  if (swissRounds === null && topCut === null) return null;

  return {
    swissRounds: swissRounds ?? FALLBACK_SWISS_ROUNDS,
    topCut: topCut ?? FALLBACK_TOP_CUT,
    source: "event_page",
  };
}

export function defaultTournamentStructureForPlayerCount(playerCount: number): TournamentStructureDefaults {
  if (playerCount <= 0) {
    return {
      swissRounds: FALLBACK_SWISS_ROUNDS,
      topCut: FALLBACK_TOP_CUT,
      source: "fallback",
    };
  }

  if (playerCount <= 16) return { swissRounds: 2, topCut: 0, source: "fallback" };
  if (playerCount <= 34) return { swissRounds: 3, topCut: 4, source: "fallback" };
  if (playerCount <= 64) return { swissRounds: 4, topCut: 10, source: "fallback" };
  if (playerCount <= 128) return { swissRounds: 5, topCut: 16, source: "fallback" };
  if (playerCount <= 208) return { swissRounds: 6, topCut: 16, source: "fallback" };
  if (playerCount <= 304) return { swissRounds: 7, topCut: 16, source: "fallback" };
  if (playerCount <= 540) return { swissRounds: 8, topCut: 16, source: "fallback" };
  if (playerCount <= 960) return { swissRounds: 9, topCut: 16, source: "fallback" };
  return { swissRounds: 10, topCut: 16, source: "fallback" };
}

export async function fetchTournamentStructureDefaults(
  slug: string,
  playerCount = 0
): Promise<TournamentStructureDefaults> {
  for (const url of [
    `https://topdeck.gg/event/${slug}`.trim(),
    `https://topdeck.gg/bracket/${slug}`.trim(),
  ]) {
    const response = await fetch(url, {
      next: { revalidate: 60 * 15 },
    });

    if (response.ok) {
      const inferred = inferTournamentStructureFromText(await response.text());
      if (inferred) return inferred;
    }
  }

  return defaultTournamentStructureForPlayerCount(playerCount);
}

export function extractTournamentSlug(input: string): string {
  const value = input.trim();
  if (!value) return "";
  if (!value.includes("/") && !value.includes(".")) return value;

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
  const res = await fetch(CHAMPIONSHIP_LEADERBOARD_URL, { next: { revalidate: 60 * 15 } });
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

export async function fetchTopDeckProfileStats(topdeckId: string): Promise<TopDeckProfileStats | null> {
  const res = await fetch(`https://topdeck.gg/profile/${encodeURIComponent(topdeckId)}/stats`, {
    next: { revalidate: 60 * 15 },
  });
  if (!res.ok) {
    throw new Error(`TopDeck profile stats fetch failed (${res.status})`);
  }

  const payload = (await res.json()) as TopDeckProfileStatsResponse;
  const yearlyStats = payload.yearlyStats ?? {};
  const totals = Object.values(yearlyStats).reduce(
    (current, year) => {
      const edhStats = year["Magic: The Gathering: EDH"] ?? year.overall;
      if (!edhStats) return current;
      current.tournaments += edhStats.totalTournaments ?? 0;
      current.wins += edhStats.wins ?? 0;
      current.draws += edhStats.draws ?? 0;
      current.losses += edhStats.losses ?? 0;
      return current;
    },
    { tournaments: 0, wins: 0, draws: 0, losses: 0 }
  );
  const gamesPlayed = totals.wins + totals.draws + totals.losses;
  if (totals.tournaments === 0 && gamesPlayed === 0) return null;

  return {
    tournaments: totals.tournaments,
    gamesPlayed,
    wins: totals.wins,
    draws: totals.draws,
    losses: totals.losses,
  };
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

function readFirestoreUnixSeconds(field: FirestoreFieldValue | undefined) {
  if (!field) return null;
  if (typeof field.integerValue === "string") {
    const parsed = Number(field.integerValue);
    return Number.isFinite(parsed) ? parsed : null;
  }
  if (typeof field.doubleValue === "number" && Number.isFinite(field.doubleValue)) {
    return field.doubleValue;
  }
  return null;
}

async function fetchTopDeckEventTiming(slug: string): Promise<{ startDate: number | null; endDate: number | null }> {
  const url =
    `https://firestore.googleapis.com/v1/projects/${TOPDECK_FIRESTORE_PROJECT_ID}` +
    `/databases/(default)/documents/otherEvents/${encodeURIComponent(slug)}?key=${TOPDECK_FIRESTORE_API_KEY}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    return { startDate: null, endDate: null };
  }

  const payload = (await res.json()) as {
    fields?: {
      startDate?: FirestoreFieldValue;
      endDate?: FirestoreFieldValue;
    };
  };

  return {
    startDate: readFirestoreUnixSeconds(payload.fields?.startDate),
    endDate: readFirestoreUnixSeconds(payload.fields?.endDate),
  };
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

  const eventTiming = await fetchTopDeckEventTiming(slug);
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
      startDate: eventTiming.startDate ?? "",
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
