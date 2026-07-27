import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { RegionalLeaderboardTable } from "@/app/regional-elo/regional-leaderboard-table";

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
  global_elo_game_results: [
    { game_id: "eligible-1", topdeck_id: "player-1-topdeck", result: "win", ranking_eligible: true, all_eligible: true },
    { game_id: "eligible-2", topdeck_id: "player-1-topdeck", result: "loss", ranking_eligible: true, all_eligible: true },
    { game_id: "eligible-3", topdeck_id: "player-1-topdeck", result: "draw", ranking_eligible: true, all_eligible: true },
    { game_id: "ineligible-1", topdeck_id: "player-1-topdeck", result: "win", ranking_eligible: false, all_eligible: true },
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
  private limitCount: number | null = null;

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

  limit(count: number) {
    this.limitCount = count;
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
    if (this.limitCount !== null) {
      rows = rows.slice(0, this.limitCount);
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

type ReactElementLike = { type: unknown; props?: { children?: unknown } };

function isReactElementLike(value: unknown): value is ReactElementLike {
  return typeof value === "object" && value !== null && "type" in value;
}

// Walks a React element tree (without rendering it) collecting every element whose `type`
// matches `target`. Used to inspect the exact props a client component receives, since that's
// what gets serialized into the page's payload — see issue #253.
function findElementsOfType(node: unknown, target: unknown, found: ReactElementLike[] = []) {
  if (node === null || node === undefined || typeof node === "boolean") return found;
  if (Array.isArray(node)) {
    for (const child of node) findElementsOfType(child, target, found);
    return found;
  }
  if (isReactElementLike(node)) {
    if (node.type === target) found.push(node);
    if (node.props && "children" in node.props) {
      findElementsOfType(node.props.children, target, found);
    }
  }
  return found;
}

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
    expect(html).toMatch(/Games<\/th>[\s\S]*?>3<\/td>/);
    expect(html).toContain("Show 30+ player games only");
  });

  it("uses all leaderboard counters when the filter is explicitly disabled", async () => {
    const pageModule = await import("@/app/regional-elo/page");
    const element = await pageModule.default({
      searchParams: { scope: "global", eloOnly: "false" },
    });

    const html = renderToStaticMarkup(element);

    expect(html).toMatch(/Games<\/th>[\s\S]*?>4<\/td>/);
    expect(html).toContain('aria-checked="false"');
  });

  it("renders 'No commander data' and 'No tournament data' when enriched profile rows are missing", async () => {
    // Clear the profile data for this test
    const originalProfiles = [...tableData.player_commander_profiles];
    tableData.player_commander_profiles = [];
    
    try {
      const pageModule = await import("@/app/regional-elo/page");
      const element = await pageModule.default({
        searchParams: { scope: "global" },
      });

      const html = renderToStaticMarkup(element);

      expect(html).toContain("Jason Doan // CriticalEDH");
      expect(html).toContain("No commander data");
      expect(html).toContain("No tournament data");
    } finally {
      tableData.player_commander_profiles = originalProfiles;
    }
  });

  it("never passes the internal `rating` field to the client leaderboard table", async () => {
    const pageModule = await import("@/app/regional-elo/page");
    const element = await pageModule.default({
      searchParams: { scope: "global" },
    });

    const tableElements = findElementsOfType(element, RegionalLeaderboardTable);
    expect(tableElements.length).toBeGreaterThan(0);

    for (const tableElement of tableElements) {
      const { leaderboard } = tableElement.props as { leaderboard: Array<Record<string, unknown>> };
      expect(leaderboard.length).toBeGreaterThan(0);
      for (const row of leaderboard) {
        expect(row).not.toHaveProperty("rating");
      }
    }
  });

  it("strips `rating` when normalizing a Supabase row into a client-safe leaderboard row", async () => {
    const pageModule = await import("@/app/regional-elo/page");
    const clientRow = pageModule.toClientLeaderboardRow({
      region_type: "global",
      region_key: "ALL",
      player_id: "player-1",
      player_name: "Test Player",
      topdeck_id: "player-1-topdeck",
      rating: 1734.864,
      games_played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      last_game_date: null,
      rank: 1,
      topdeck_elo: 2000,
      topdeck_elo_rank: 1,
    });

    expect(clientRow).not.toHaveProperty("rating");
    expect(clientRow.player_name).toBe("Test Player");
  });

  it("strips a legacy `hidden_rating` field left over from a stale pre-deploy cache entry", async () => {
    const pageModule = await import("@/app/regional-elo/page");
    // Simulate a `regional-elo-leaderboard-v4` cache entry written by the old
    // `normalizeLeaderboardRows`, which used to copy `rating` onto `hidden_rating`. TypeScript's
    // static `LeaderboardRow` type no longer has this field, but a runtime cache hit could still
    // carry it until the cache naturally expires — `toClientLeaderboardRow` must defend against
    // that regardless of the declared type.
    const staleRowFromCache = {
      region_type: "global",
      region_key: "ALL",
      player_id: "player-1",
      player_name: "Test Player",
      topdeck_id: "player-1-topdeck",
      rating: 1734.864,
      hidden_rating: 1734.864,
      games_played: 1,
      wins: 1,
      draws: 0,
      losses: 0,
      last_game_date: null,
      rank: 1,
      topdeck_elo: 2000,
      topdeck_elo_rank: 1,
    } as Parameters<typeof pageModule.toClientLeaderboardRow>[0];

    const clientRow = pageModule.toClientLeaderboardRow(staleRowFromCache);

    expect(clientRow).not.toHaveProperty("rating");
    expect(clientRow).not.toHaveProperty("hidden_rating");
    expect(clientRow.player_name).toBe("Test Player");
  });
});
