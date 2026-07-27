import { beforeEach, describe, expect, it, vi } from "vitest";

type QueryState = {
  table: string;
  select?: string;
  filters: Array<{ column: string; values: unknown }>;
  range?: [number, number];
};

const { fromMock } = vi.hoisted(() => ({
  fromMock: vi.fn(),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: { from: fromMock },
}));

import {
  convertToCSV,
  exportMatchupSummary,
  exportPlayerMatchups,
} from "@/lib/exports/player-matchups";

const player = {
  id: "player-1",
  name: "Player One",
  topdeck_id: "player-topdeck-id",
};

function makeLargeHistory() {
  const ownRows = Array.from({ length: 1001 }, (_, index) => ({
    game_id: `game-${index}`,
    entry_id: "entry-1",
    result: "win",
  }));
  const games = ownRows.map((row) => ({
    id: row.game_id,
    tournament_id: "tournament-1",
    status: "completed",
  }));

  return { ownRows, games };
}

function configureSupabaseMock(options: {
  error?: { table: string; column?: string };
  ownRanges: Array<[number, number]>;
}) {
  const { ownRows, games } = makeLargeHistory();

  fromMock.mockImplementation((table: string) => {
    const state: QueryState = { table, filters: [] };
    const query = {
      select: (select: string) => {
        state.select = select;
        return query;
      },
      ilike: (column: string, values: unknown) => {
        state.filters.push({ column, values });
        return query;
      },
      eq: (column: string, values: unknown) => {
        state.filters.push({ column, values });
        return query;
      },
      in: (column: string, values: unknown[]) => {
        state.filters.push({ column, values });
        return query;
      },
      limit: () => query,
      range: (from: number, to: number) => {
        state.range = [from, to];
        return query;
      },
      then: (
        onFulfilled: (value: unknown) => unknown,
        onRejected?: (reason: unknown) => unknown
      ) => {
        try {
          if (
            options.error?.table === table &&
            (!options.error.column ||
              state.filters.some(({ column }) => column === options.error?.column))
          ) {
            throw new Error(`${table} query failed`);
          }

          const filter = (column: string) =>
            state.filters.find((item) => item.column === column)?.values;

          let data: unknown[] = [];
          if (table === "players" && !filter("id")) {
            data = [player];
          } else if (table === "tournament_entries" && filter("player_id")) {
            data = [
              {
                id: "entry-1",
                player_id: player.id,
                tournament_id: "tournament-1",
                decklist_text: "decklist",
                decklist_url: null,
              },
            ];
          } else if (table === "game_participants" && filter("entry_id")) {
            const range = state.range ?? [0, 999];
            options.ownRanges.push([range[0], range[1]]);
            data = ownRows.slice(range[0], range[1] + 1);
          } else if (table === "game_participants" && filter("game_id")) {
            const gameIds = filter("game_id") as string[];
            data = gameIds.flatMap((gameId) => [
              { game_id: gameId, entry_id: "entry-1", result: "win" },
              {
                game_id: gameId,
                entry_id: `opponent-entry-${gameId.slice(5)}`,
                result: "loss",
              },
            ]);
          } else if (table === "games") {
            const gameIds = filter("id") as string[];
            data = games.filter((game) => gameIds.includes(game.id));
          } else if (table === "tournaments") {
            data = [
              {
                id: "tournament-1",
                name: "Large Tournament",
                start_date: "2026-01-01T00:00:00Z",
                topdeck_tid: "large-tournament",
                player_count: 100,
              },
            ];
          } else if (table === "tournament_entries" && filter("id")) {
            const entryIds = filter("id") as string[];
            data = entryIds.map((id) => ({
              id,
              player_id: `opponent-player-${id.replace("opponent-entry-", "")}`,
            }));
          } else if (table === "players" && filter("id")) {
            const playerIds = filter("id") as string[];
            data = playerIds.map((id) => ({
              id,
              name: `Opponent ${id.replace("opponent-player-", "")}`,
              topdeck_id: `${id}-topdeck`,
            }));
          }

          return Promise.resolve(onFulfilled({ data, error: null }));
        } catch (error) {
          return onRejected ? Promise.resolve(onRejected(error)) : Promise.reject(error);
        }
      },
    };

    return query;
  });
}

describe("player matchup exports", () => {
  beforeEach(() => {
    fromMock.mockReset();
  });

  it("neutralizes spreadsheet formulas while preserving zero values", () => {
    const csv = convertToCSV([
      {
        equals: "=SUM(A1:A2)",
        plus: "+malicious",
        minus: "-malicious",
        at: "@malicious",
        zero: 0,
        empty: null,
      },
    ]);

    expect(csv).toBe(
      "equals,plus,minus,at,zero,empty\n'=SUM(A1:A2),'+malicious,'-malicious,'@malicious,0,"
    );
  });

  it.each([
    ["detailed", exportPlayerMatchups],
    ["summary", exportMatchupSummary],
  ] as const)(
    "pages the player's own participant history for %s exports",
    async (_label, exporter) => {
      const ownRanges: Array<[number, number]> = [];
      configureSupabaseMock({ ownRanges });

      const result = await exporter("Player One", "json", "ranking");

      expect(ownRanges).toEqual([
        [0, 999],
        [1000, 1999],
      ]);
      expect(JSON.parse(result ?? "[]")).toHaveLength(1001);
    }
  );

  it.each([
    exportPlayerMatchups,
    exportMatchupSummary,
  ])("propagates Supabase errors for %s exports", async (exporter) => {
    configureSupabaseMock({
      ownRanges: [],
      error: { table: "game_participants", column: "entry_id" },
    });

    await expect(exporter("Player One", "json", "ranking")).rejects.toThrow(
      "game_participants query failed"
    );
  });
});
