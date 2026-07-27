import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  rows: [] as Array<{ topdeck_id: string; result: string }>,
  ranges: [] as Array<[number, number]>,
  eligibilityColumns: [] as string[],
  error: null as Error | null,
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: vi.fn(() => {
      const query = {
        select: () => query,
        in: () => query,
        eq: (column: string) => {
          if (column.endsWith("_eligible")) state.eligibilityColumns.push(column);
          return query;
        },
        order: () => query,
        range: (start: number, end: number) => {
          state.ranges.push([start, end]);
          return query;
        },
        then: (
          onfulfilled?: (value: { data: unknown[]; error: Error | null }) => unknown
        ) =>
          Promise.resolve({
            data: state.rows.slice(state.ranges.at(-1)?.[0] ?? 0, (state.ranges.at(-1)?.[1] ?? -1) + 1),
            error: state.error,
          }).then(onfulfilled),
      };
      return query;
    }),
  },
}));

import { fetchEloDisplayStats } from "@/lib/elo-display-stats";

describe("fetchEloDisplayStats", () => {
  beforeEach(() => {
    state.rows = [];
    state.ranges = [];
    state.eligibilityColumns = [];
    state.error = null;
  });

  it("paginates at the Supabase boundary and preserves all eligible W-L-D rows", async () => {
    state.rows = [
      { topdeck_id: "player-1", result: "win" },
      ...Array.from({ length: 1000 }, () => ({ topdeck_id: "player-1", result: "loss" })),
      { topdeck_id: "player-1", result: "draw" },
      { topdeck_id: "player-1", result: "bye" },
    ];

    const stats = await fetchEloDisplayStats(["player-1"]);

    expect(stats.get("player-1")).toEqual({
      games_played: 1002,
      wins: 1,
      draws: 1,
      losses: 1000,
    });
    expect(state.ranges).toEqual([
      [0, 999],
      [1000, 1999],
    ]);
    expect(state.eligibilityColumns).toEqual(["ranking_eligible", "ranking_eligible"]);
  });

  it("uses all-game eligibility for the explicit drill-down", async () => {
    state.rows = [{ topdeck_id: "player-1", result: "win" }];

    await fetchEloDisplayStats(["player-1"], "all");

    expect(state.eligibilityColumns).toEqual(["all_eligible"]);
  });

  it("propagates a failed display aggregate query", async () => {
    state.error = new Error("database unavailable");

    await expect(fetchEloDisplayStats(["player-1"])).rejects.toThrow(
      "Elo display stats query failed: database unavailable"
    );
  });
});
