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
  ],
  regional_elo_leaderboard: [
    {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-1",
      topdeck_id: "CCIQroaCHHQi7EELyNXlHiHQiQy1",
      rank: 6,
      rating: 1734.864,
      games_played: 3,
      wins: 1,
      draws: 1,
      losses: 1,
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
  ],
  tournaments: [
    { id: "tournament-1", name: "California Open I", start_date: "2026-04-03", state: "California" },
    { id: "tournament-2", name: "California Open II", start_date: "2026-04-02", state: "California" },
    { id: "tournament-3", name: "California Open III", start_date: "2026-04-01", state: "California" },
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
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: (table: string) => new MockQuery(table),
  },
}));

describe("RegionalPlayerPage", () => {
  it("renders summary cards and regional rankings from the same canonical counts", async () => {
    const pageModule = await import("@/app/regional-elo/player/[topdeckId]/page");
    const element = await pageModule.default({
      params: { topdeckId: "CCIQroaCHHQi7EELyNXlHiHQiQy1" },
      searchParams: { region: "CALIFORNIA" },
    });

    const html = renderToStaticMarkup(element);

    expect(html).toContain("Alex Lien");
    expect(html).toContain("TopDeck Rank");
    expect(html).toContain("Region Rank");
    expect(html).toContain("Active region");
    expect(html).toContain(
      "Elo and rank use the global all-games leaderboard. Region Rank groups players by active profile region"
    );
    expect(html).toMatch(/Games[\s\S]*?>3</);
    expect(html).toMatch(/Record[\s\S]*?>1-1-1</);
    expect(html).toMatch(/CALIFORNIA[\s\S]*?Active region[\s\S]*?>3<[\s\S]*?>1-1-1</);
  });
});
