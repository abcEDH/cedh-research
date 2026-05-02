import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

type TableData = Record<string, Array<Record<string, unknown>>>;

const tableData: TableData = {
  global_elo_regions: [
    {
      region_type: "global",
      region_key: "ALL",
      country_key: null,
      player_count: 1,
      updated_at: "2026-04-26T00:00:00Z",
    },
  ],
  global_elo_active_leaderboard: [
    {
      region_type: "global",
      region_key: "ALL",
      country_key: null,
      primary_country_key: "UNITED STATES",
      primary_region_key: "CALIFORNIA",
      player_id: "player-1",
      player_name: "Jason Doan // CriticalEDH",
      topdeck_id: "player-1-topdeck",
      rating: 1734.864,
      games_played: 754,
      wins: 372,
      draws: 177,
      losses: 205,
      last_game_date: "2026-04-24",
      rank: 1,
      topdeck_elo: 2014.2,
      topdeck_elo_rank: 1,
    },
  ],
  player_commander_profiles: [
    {
      topdeck_id: "player-1-topdeck",
      active_commander: "Kinnan, Bonder Prodigy",
      latest_decklist_url: "https://topdeck.gg/deck/event-1/player-1-topdeck",
      latest_tournament_name: "LEVEL SEVEN'S WEEKLY CEDH EVENT",
      latest_tournament_date: "2026-04-25",
      latest_tournament_topdeck_tid: "event-1",
    },
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

  constructor(private table: string) {}

  select() {
    return this;
  }

  eq(column: string, value: unknown) {
    this.filters.push((row) => row[column] === value);
    return this;
  }

  in(column: string, values: unknown[]) {
    this.filters.push((row) => values.includes(row[column]));
    return this;
  }

  ilike() {
    return this;
  }

  order(column: string, options?: { ascending?: boolean; nullsFirst?: boolean }) {
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
    return { data: rows, error: null, count: rows.length };
  }

  then<TResult1 = { data: unknown; error: Error | null; count: number }, TResult2 = never>(
    onfulfilled?:
      | ((value: { data: unknown; error: Error | null; count: number }) => TResult1 | PromiseLike<TResult1>)
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

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: (table: string) => new MockQuery(table),
  },
}));

describe("RegionalEloPage", () => {
  it("renders commander and latest tournament data when the enriched profile rows are present", async () => {
    const pageModule = await import("@/app/regional-elo/page");
    const element = await pageModule.default({
      searchParams: { scope: "global" },
    });

    const html = renderToStaticMarkup(element);

    expect(html).toContain("Jason Doan // CriticalEDH");
    expect(html).toContain("Kinnan, Bonder Prodigy");
    expect(html).toMatch(/LEVEL SEVEN(?:'|&#x27;)S WEEKLY CEDH EVENT/);
    expect(html).not.toContain("No commander data");
    expect(html).not.toContain("No tournament data");
  });
});
