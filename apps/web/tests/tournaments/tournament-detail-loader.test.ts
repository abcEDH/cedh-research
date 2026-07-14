import { describe, expect, it, vi } from "vitest";

type TableData = Record<string, Array<Record<string, unknown>>>;

const tableData: TableData = {
  tournaments: [
    {
      id: "t-1",
      topdeck_tid: "merlion-anniversary-cedh",
      name: '"Win a Mox Diamond" Merlion Anniversary CEDH Event',
      start_date: "2026-07-11",
      player_count: 23,
      swiss_rounds: 5,
      top_cut: 16,
    },
  ],
  tournament_entries: [
    {
      final_standing: 1,
      tournament_id: "t-1",
      // TopDeck reports only `points` for this event — no explicit W/L/D.
      wins: null,
      losses: null,
      draws: null,
      points: 1866,
      decklist_url: null,
      made_top_cut: true,
      made_top_16: true,
      players: { name: "Luca Ratra", topdeck_id: "p-1", topdeck_handle: null },
      commanders: { name: "Rograkh, Son of Rohgahh", color_identity: ["R", "U", "B"] },
    },
    {
      final_standing: 2,
      tournament_id: "t-1",
      // A normal entry with explicit W/L/D, unrelated to `points`.
      wins: 4,
      losses: 1,
      draws: 0,
      points: 20,
      decklist_url: null,
      made_top_cut: true,
      made_top_16: true,
      players: { name: "Second Place", topdeck_id: "p-2", topdeck_handle: null },
      commanders: { name: "Some Commander", color_identity: ["W"] },
    },
  ],
};

class MockQuery {
  private filters: Array<(row: Record<string, unknown>) => boolean> = [];
  private orderColumn: string | null = null;
  private orderAscending = true;
  private limitCount: number | null = null;
  private expectSingle = false;

  constructor(private table: string) {}

  select() {
    return this;
  }

  eq(column: string, value: unknown) {
    this.filters.push((row) => row[column] === value);
    return this;
  }

  order(column: string, options?: { ascending?: boolean }) {
    this.orderColumn = column;
    this.orderAscending = options?.ascending ?? true;
    return this;
  }

  limit(count: number) {
    this.limitCount = count;
    return this;
  }

  maybeSingle() {
    this.expectSingle = true;
    return this;
  }

  private execute() {
    let rows = (tableData[this.table] ?? []).filter((row) => this.filters.every((filter) => filter(row)));
    if (this.orderColumn) {
      const column = this.orderColumn;
      const direction = this.orderAscending ? 1 : -1;
      rows = [...rows].sort((a, b) => {
        const left = a[column] as number | null;
        const right = b[column] as number | null;
        if (left === right) return 0;
        if (left === null) return 1;
        if (right === null) return -1;
        return left > right ? direction : -direction;
      });
    }
    if (this.limitCount !== null) rows = rows.slice(0, this.limitCount);

    if (this.expectSingle) {
      return { data: rows[0] ?? null, error: null };
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

vi.mock("server-only", () => ({}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: (table: string) => new MockQuery(table),
  },
}));

describe("loadTournamentDetail", () => {
  it("does not derive wins/draws from points when TopDeck omits explicit W/L/D", async () => {
    const { loadTournamentDetail } = await import("@/lib/tournament-detail-loader");
    const detail = await loadTournamentDetail("merlion-anniversary-cedh");

    expect(detail).not.toBeNull();
    const winner = detail!.standings[0];

    // Regression guard: points=1866 must never be split into a fabricated
    // 373-0-1 record via wins=Math.floor(points/5), draws=points%5. Point
    // scoring formulas vary per tournament/organizer and are not a reliable
    // stand-in for an explicit record.
    expect(winner.wins).toBe(0);
    expect(winner.losses).toBe(0);
    expect(winner.draws).toBe(0);
    expect(winner.points).toBe(1866);
  });

  it("passes through explicit wins/losses/draws untouched, independent of points", async () => {
    const { loadTournamentDetail } = await import("@/lib/tournament-detail-loader");
    const detail = await loadTournamentDetail("merlion-anniversary-cedh");

    const second = detail!.standings[1];
    expect(second.wins).toBe(4);
    expect(second.losses).toBe(1);
    expect(second.draws).toBe(0);
    expect(second.points).toBe(20);
  });
});
