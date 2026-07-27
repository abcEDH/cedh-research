import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

type TableData = Record<string, Array<Record<string, unknown>>>;

const tableData: TableData = {
  players: [
    { id: "player-1", name: "Alex Lien", topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1" },
    { id: "player-2", name: "Opponent A", topdeck_id: "opp-a" },
    { id: "player-3", name: "Opponent B", topdeck_id: "opp-b" },
    { id: "player-4", name: "Opponent C", topdeck_id: "opp-c" },
    { id: "player-5", name: "Unknown Region Player", topdeck_id: "unknown-region-player" },
    { id: "player-6", name: "Inactive Player", topdeck_id: "inactive-player" },
  ],
  global_elo_active_leaderboard: [
    {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-1",
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      primary_country_key: "UNITED STATES",
      primary_region_key: "CALIFORNIA",
      rank: 6,
      topdeck_elo_rank: 4,
      rating: 1734.864,
      topdeck_elo: 1900.066,
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
    },
    {
      region_type: "country",
      region_key: "UNITED STATES",
      player_id: "player-1",
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      primary_country_key: "UNITED STATES",
      primary_region_key: "CALIFORNIA",
      rank: 4,
      topdeck_elo_rank: 2,
      rating: 1734.864,
      topdeck_elo: 1900.066,
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
    },
    {
      region_type: "state",
      region_key: "CALIFORNIA",
      country_key: "UNITED STATES",
      player_id: "player-1",
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      primary_country_key: "UNITED STATES",
      primary_region_key: "CALIFORNIA",
      rank: 5,
      topdeck_elo_rank: 3,
      rating: 1734.864,
      topdeck_elo: 1900.066,
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
    },
    {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-6",
      topdeck_id: "inactive-player",
      primary_country_key: "UNITED STATES",
      primary_region_key: "CALIFORNIA",
      rank: 99,
      topdeck_elo_rank: 88,
      rating: 1600,
      topdeck_elo: 1501.5,
      games_played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      last_game_date: "2025-01-01",
    },
  ],
  global_elo_player_profile_summaries: [
    {
      player_id: "player-1",
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
      home_country_key: "UNITED STATES",
      home_region_key: "CALIFORNIA",
      state_assignments: [
        {
          country_key: "UNITED STATES",
          region_key: "CALIFORNIA",
          games_played: 3,
          wins: 1,
          draws: 1,
          losses: 1,
        },
      ],
    },
    {
      player_id: "player-5",
      games_played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      last_game_date: "2026-04-04",
      home_country_key: "UNKNOWN",
      home_region_key: "UNKNOWN",
      state_assignments: [
        {
          country_key: "UNKNOWN",
          region_key: "UNKNOWN",
          games_played: 1,
          wins: 1,
          draws: 0,
          losses: 0,
        },
      ],
    },
  ],
  player_commander_profiles: [
    {
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      active_commander: "Rograkh / Silas",
      latest_decklist_url: "https://topdeck.gg/deck/tournament-1/CCIQroaCHHQi7EELyNXlHiHQiQy1",
      latest_tournament_name: "California Open I",
      latest_tournament_date: "2026-04-03",
      latest_tournament_topdeck_tid: "tournament-1",
    },
    {
      topdeck_id: "unknown-region-player",
      active_commander: "Rograkh / Silas",
      latest_decklist_url: null,
      latest_tournament_name: "Unknown Region Open",
      latest_tournament_date: "2026-04-04",
      latest_tournament_topdeck_tid: "tournament-4",
    },
  ],
  global_elo_leaderboard: [
    {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-1",
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      primary_region_key: "CALIFORNIA",
      rank: 6,
      rating: 1734.864,
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
    },
    {
      region_type: "state",
      region_key: "CALIFORNIA",
      player_id: "player-1",
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      rank: 3,
      rating: 1734.864,
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
    },
    {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-2",
      topdeck_id: "opp-a",
      rank: 176,
      rating: 1518.476,
      games_played: 2,
      wins: 0,
      draws: 1,
      losses: 1,
      last_game_date: "2026-04-03",
    },
    {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-6",
      topdeck_id: "inactive-player",
      primary_region_key: "CALIFORNIA",
      rank: 99,
      rating: 1600,
      games_played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      last_game_date: "2025-01-01",
    },
    {
      region_type: "state",
      region_key: "CALIFORNIA",
      player_id: "player-6",
      topdeck_id: "inactive-player",
      rank: 44,
      rating: 1600,
      games_played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      last_game_date: "2025-01-01",
    },
  ],
  tournament_entries: [
    {
      id: "entry-1",
      tournament_id: "tournament-1",
      player_id: "player-1",
      commander_id: "cmd-1",
      tournaments: { start_date: "2026-04-03", state: "California", player_count: 32 },
    },
    {
      id: "entry-2",
      tournament_id: "tournament-2",
      player_id: "player-1",
      commander_id: "cmd-1",
      tournaments: { start_date: "2026-04-02", state: "California", player_count: 32 },
    },
    {
      id: "entry-3",
      tournament_id: "tournament-3",
      player_id: "player-1",
      commander_id: "cmd-1",
      tournaments: { start_date: "2026-04-01", state: "California", player_count: 32 },
    },
    { id: "entry-4", tournament_id: "tournament-1", player_id: "player-2", commander_id: "cmd-2" },
    { id: "entry-5", tournament_id: "tournament-2", player_id: "player-2", commander_id: "cmd-2" },
    { id: "entry-6", tournament_id: "tournament-3", player_id: "player-3", commander_id: "cmd-3" },
    { id: "entry-7", tournament_id: "tournament-1", player_id: "player-3", commander_id: "cmd-3" },
    { id: "entry-8", tournament_id: "tournament-2", player_id: "player-4", commander_id: "cmd-4" },
    { id: "entry-9", tournament_id: "tournament-4", player_id: "player-5", commander_id: "cmd-1" },
    { id: "entry-10", tournament_id: "tournament-5", player_id: "player-6", commander_id: "cmd-1" },
  ],
  game_participants: [
    { game_id: "game-1", entry_id: "entry-1", seat_position: 0, result: "win" },
    { game_id: "game-1", entry_id: "entry-4", seat_position: 1, result: "loss" },
    { game_id: "game-1", entry_id: "entry-7", seat_position: 2, result: "loss" },
    { game_id: "game-2", entry_id: "entry-2", seat_position: 1, result: "loss" },
    { game_id: "game-2", entry_id: "entry-5", seat_position: 0, result: "win" },
    { game_id: "game-2", entry_id: "entry-8", seat_position: 3, result: "loss" },
    { game_id: "game-3", entry_id: "entry-3", seat_position: 3, result: "draw" },
    { game_id: "game-3", entry_id: "entry-6", seat_position: 1, result: "draw" },
    { game_id: "game-4", entry_id: "entry-9", seat_position: 0, result: "win" },
    { game_id: "game-5", entry_id: "entry-10", seat_position: 0, result: "win" },
  ],
  games: [
    {
      id: "game-1",
      tournament_id: "tournament-1",
      round_number: 1,
      round_name: null,
      table_number: 1,
      is_draw: false,
      winner_id: "entry-1",
    },
    {
      id: "game-2",
      tournament_id: "tournament-2",
      round_number: 2,
      round_name: null,
      table_number: 2,
      is_draw: false,
      winner_id: "entry-5",
    },
    {
      id: "game-3",
      tournament_id: "tournament-3",
      round_number: 3,
      round_name: null,
      table_number: 3,
      is_draw: true,
      winner_id: null,
    },
    {
      id: "game-4",
      tournament_id: "tournament-4",
      round_number: 1,
      round_name: null,
      table_number: 1,
      is_draw: false,
      winner_id: "entry-9",
    },
    {
      id: "game-5",
      tournament_id: "tournament-5",
      round_number: 1,
      round_name: null,
      table_number: 1,
      is_draw: false,
      winner_id: "entry-10",
    },
  ],
  tournaments: [
    { id: "tournament-1", name: "California Open I", start_date: "2026-04-03", state: "California", player_count: 32 },
    { id: "tournament-2", name: "California Open II", start_date: "2026-04-02", state: "California", player_count: 29 },
    { id: "tournament-3", name: "California Open III", start_date: "2026-04-01", state: "California", player_count: 32 },
    { id: "tournament-4", name: "Unknown Region Open", start_date: "2026-04-04", state: null, player_count: 12 },
    { id: "tournament-5", name: "Inactive Open", start_date: "2025-01-01", state: "California", player_count: 32 },
  ],
  commanders: [
    { id: "cmd-1", name: "Rograkh / Silas" },
    { id: "cmd-2", name: "Blue Farm" },
    { id: "cmd-3", name: "Nadu" },
    { id: "cmd-4", name: "Kinnan" },
  ],
};

function applyFilters(rows: Array<Record<string, unknown>>, filters: Array<(row: Record<string, unknown>) => boolean>) {
  return rows.filter((row) => filters.every((filter) => filter(row)));
}

class MockQuery {
  private filters: Array<(row: Record<string, unknown>) => boolean> = [];
  private orderColumn: string | null = null;
  private orderAscending = true;
  private rangeStart: number | null = null;
  private rangeEnd: number | null = null;
  private expectSingle = false;
  private allowMissing = false;

  constructor(private table: string) {}

  select() {
    return this;
  }

  eq(column: string, value: unknown) {
    this.filters.push((row) => row[column] === value);
    return this;
  }

  neq(column: string, value: unknown) {
    this.filters.push((row) => row[column] !== value);
    return this;
  }

  gte(column: string, value: unknown) {
    this.filters.push((row) => String(row[column] ?? "") >= String(value));
    return this;
  }

  not(column: string, operator: string, value: unknown) {
    if (column.includes(".")) return this;
    if (operator === "is" && value === null) {
      this.filters.push((row) => row[column] !== null && row[column] !== undefined);
    }
    return this;
  }

  in(column: string, values: unknown[]) {
    this.filters.push((row) => values.includes(row[column]));
    return this;
  }

  ilike(column: string, value: string) {
    const normalized = value.toLowerCase();
    this.filters.push((row) => String(row[column] ?? "").toLowerCase() === normalized);
    return this;
  }

  order(column: string, options?: { ascending?: boolean }) {
    this.orderColumn = column;
    this.orderAscending = options?.ascending ?? true;
    return this;
  }

  range(start: number, end: number) {
    this.rangeStart = start;
    this.rangeEnd = end;
    return this;
  }

  maybeSingle() {
    this.expectSingle = true;
    this.allowMissing = true;
    return this;
  }

  single() {
    this.expectSingle = true;
    this.allowMissing = false;
    return this;
  }

  private execute() {
    let rows = applyFilters([...(tableData[this.table] ?? [])], this.filters);
    if (this.orderColumn) {
      const column = this.orderColumn;
      const direction = this.orderAscending ? 1 : -1;
      rows.sort((a, b) => {
        const left = a[column];
        const right = b[column];
        if (left === right) return 0;
        return left! > right! ? direction : -direction;
      });
    }
    if (this.rangeStart !== null && this.rangeEnd !== null) {
      rows = rows.slice(this.rangeStart, this.rangeEnd + 1);
    }

    if (this.expectSingle) {
      const row = rows[0] ?? null;
      if (!row && !this.allowMissing) {
        return { data: null, error: new Error(`No rows found for ${this.table}`) };
      }
      return { data: row, error: null };
    }

    return { data: rows, error: null };
  }

  then<TResult1 = { data: unknown; error: Error | null }, TResult2 = never>(
    onfulfilled?:
      | ((value: { data: unknown; error: Error | null }) => TResult1 | PromiseLike<TResult1>)
      | null,
    onrejected?: ((reason: unknown) => TResult2 | PromiseLike<TResult2>) | null
  ) {
    return Promise.resolve(this.execute()).then(onfulfilled, onrejected);
  }
}

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href, ...props }, children),
}));

vi.mock("next/cache", () => ({
  unstable_cache: <T extends (...args: never[]) => unknown>(callback: T) => callback,
}));

vi.mock("server-only", () => ({}));

vi.mock("@/lib/topdeck", () => ({
  fetchChampionshipLeaderboard: vi.fn(async () => [
    {
      uid: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      rank: 40,
      points: 1255,
    },
  ]),
  fetchTopDeckProfileStats: vi.fn(async (topdeckId: string) =>
    topdeckId === "CCIQroaCHHQi7EELyNXlHiHQiQy1"
      ? { tournaments: 1, gamesPlayed: 3, wins: 1, draws: 1, losses: 1 }
      : topdeckId === "inactive-player"
        ? { tournaments: 1, gamesPlayed: 1, wins: 1, draws: 0, losses: 0 }
      : null
  ),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: (table: string) => new MockQuery(table),
  },
}));

async function renderPlayerPage(
  topdeckId: string,
  searchParams: Record<string, string | string[] | undefined> = {}
) {
  const pageModule = await import("@/app/regional-elo/player/[topdeckId]/page");
  const componentsModule = await import(
    "@/app/regional-elo/player/[topdeckId]/player-profile-components"
  );

  const wrapperElement = await pageModule.default({
    params: { topdeckId },
    searchParams,
  });
  const wrapperHtml = renderToStaticMarkup(wrapperElement);

  const player = (tableData.players ?? []).find(
    (row) => row.topdeck_id === topdeckId
  ) as { id: string; name: string; topdeck_id: string } | undefined;
  if (!player) return wrapperHtml;

  const rawRegion = searchParams.region;
  const regionParam = Array.isArray(rawRegion) ? (rawRegion[0] ?? "") : (rawRegion ?? "");
  const regionFilter = regionParam.toUpperCase() === "ALL" ? "" : regionParam.toUpperCase();

  const [headerElement, gridElement, bodyElement] = await Promise.all([
    componentsModule.PlayerHeader({ topdeckId }),
    componentsModule.PlayerProfileGrid({ topdeckId, player, regionFilter }),
    pageModule.PlayerProfileBody({ topdeckId, player, searchParams }),
  ]);

  const headerHtml = headerElement ? renderToStaticMarkup(headerElement) : "";
  const gridHtml = renderToStaticMarkup(gridElement);
  const bodyHtml = renderToStaticMarkup(bodyElement);
  return wrapperHtml + headerHtml + gridHtml + bodyHtml;
}

describe("RegionalPlayerPage", () => {
  it("renders summary cards and regional rankings from the same canonical counts", async () => {
    const html = await renderPlayerPage("CCIQroaCHHQi7EELyNXlHiHQiQy1", {
      region: "CALIFORNIA",
    });

    expect(html).toContain("Alex Lien");
    expect(html).toContain("TopDeck Rank");
    expect(html).toContain("1255 points");
    expect(html).toContain("Unique Opponents");
    expect(html).toContain("Global Rank");
    expect(html).toContain("State Rank");
    expect(html).toContain("Country Rank");
    expect(html).toContain("Home region");
    expect(html).toMatch(/TopDeck Elo[\s\S]*?>1900</);
    expect(html).toMatch(/Global Rank[\s\S]*?>#4</);
    expect(html).toMatch(/Country Rank[\s\S]*?>#2</);
    expect(html).toMatch(/Games Played[\s\S]*?>3</);
    expect(html).toMatch(/Record[\s\S]*?>1-1-1</);
    expect(html).toMatch(/CALIFORNIA[\s\S]*?Home region[\s\S]*?>3<[\s\S]*?>1-1-1</);
  });

  it("groups unknown-region games for any player profile", async () => {
    const html = await renderPlayerPage("unknown-region-player");

    expect(html).toContain("Unknown Region Player");
    expect(html).toMatch(/Games Played[\s\S]*?>1</);
    expect(html).toContain("UNKNOWN");
  });

  it("hides inactive player global and state ranks", async () => {
    const html = await renderPlayerPage("inactive-player", {
      region: "CALIFORNIA",
    });

    expect(html).toContain("Inactive Player");
    expect(html).toMatch(/State Rank[\s\S]*?>--</);
    expect(html).toMatch(/Global Rank[\s\S]*?>--</);
    expect(html).toContain("1502");
  });

  it("links opponent records to the head-to-head page", async () => {
    const html = await renderPlayerPage("CCIQroaCHHQi7EELyNXlHiHQiQy1");

    expect(html).toContain("/regional-elo/player/CCIQroaCHHQi7EELyNXlHiHQiQy1/vs/opp-a");
    expect(html).not.toContain('href="/regional-elo/player/opp-a"');
  });

  it("filters aggregate W-L-D stats to 30-player events when enabled", async () => {
    const html = await renderPlayerPage("CCIQroaCHHQi7EELyNXlHiHQiQy1", { eloOnly: "true" });

    expect(html).toContain("Show 30+ player games only");
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toMatch(/Overall[\s\S]*?>2 games[\s\S]*?>1-0-1</);
    expect(html).toContain(
      "/regional-elo/player/CCIQroaCHHQi7EELyNXlHiHQiQy1/vs/opp-a?eloOnly=true"
    );
  });

  it("updates profile game tiles to match the filtered summary", async () => {
    const componentsModule = await import(
      "@/app/regional-elo/player/[topdeckId]/player-profile-components"
    );
    const element = await componentsModule.PlayerProfileGrid({
      topdeckId: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      player: tableData.players[0] as {
        id: string;
        name: string;
        topdeck_id: string;
      },
      regionFilter: "",
      displaySummary: {
        totalGames: 2,
        totalWins: 1,
        totalDraws: 1,
        totalLosses: 0,
        seatRows: [],
        opponentRecords: [
          {
            opponentTopdeckId: "opp-a",
            opponentName: "Opponent A",
            wins: 1,
            draws: 1,
            losses: 0,
            games: 2,
          },
        ],
        commanderRecords: [],
        bestOpponentMatchup: null,
        worstOpponentMatchup: null,
        bestCommanderMatchup: null,
        worstCommanderMatchup: null,
      },
    });
    const html = renderToStaticMarkup(element);

    expect(html).toMatch(/Games Played[\s\S]*?>2</);
    expect(html).toMatch(/Record[\s\S]*?>1-0-1</);
    expect(html).toMatch(/Unique Opponents[\s\S]*?>1</);
  });
});

describe("RegionalPlayerVsPage", () => {
  it("renders the shared record and chronological pod history", async () => {
    const pageModule = await import("@/app/regional-elo/player/[topdeckId]/vs/[opponentTopdeckId]/page");
    const element = await pageModule.default({
      params: { topdeckId: "CCIQroaCHHQi7EELyNXlHiHQiQy1", opponentTopdeckId: "opp-a" },
    });

    const html = renderToStaticMarkup(element);

    expect(html).toContain("Alex Lien vs Opponent A");
    expect(html).toContain("Shared Games");
    expect(html).toContain("California Open I");
    expect(html).toContain("California Open II");
    expect(html).toContain("Round 1");
    expect(html).toContain("Round 2");
    expect(html).toContain("Table 1");
    expect(html).toContain("Table 2");
    expect(html).toContain("Rograkh / Silas");
    expect(html).toContain("Blue Farm");
    expect(html).toContain("/regional-elo/player/CCIQroaCHHQi7EELyNXlHiHQiQy1");
    expect(html).toContain("/regional-elo/player/opp-a");
    expect(html).toContain("1-1-0");
  });

  it("filters shared history and mirrored records to 30-player events", async () => {
    const pageModule = await import("@/app/regional-elo/player/[topdeckId]/vs/[opponentTopdeckId]/page");
    const element = await pageModule.default({
      params: { topdeckId: "CCIQroaCHHQi7EELyNXlHiHQiQy1", opponentTopdeckId: "opp-a" },
      searchParams: { eloOnly: "true" },
    });

    const html = renderToStaticMarkup(element);

    expect(html).toContain("Show 30+ player games only");
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toMatch(/Alex Lien Record[\s\S]*?>1-0-0</);
    expect(html).toMatch(/Opponent A Record[\s\S]*?>0-1-0</);
    expect(html).toMatch(/Shared Games[\s\S]*?>1</);
    expect(html).toContain("California Open I");
    expect(html).not.toContain("California Open II");
  });
});
