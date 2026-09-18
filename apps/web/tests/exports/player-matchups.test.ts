import { beforeEach, describe, expect, it, vi } from "vitest";

type QueryState = {
  table: string;
  select?: string;
  filters: Array<{ column: string; values: unknown }>;
  range?: [number, number];
  exactNameQuery?: boolean;
  nameLookup?: "eq" | "ilike";
  expectSingle?: boolean;
};

const { fromMock } = vi.hoisted(() => ({
  fromMock: vi.fn(),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: { from: fromMock },
}));

import {
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
  gameBatches?: number[];
  entryRanges?: Array<[number, number]>;
  entryCount?: number;
  exactPlayer?: typeof player | null;
  exactPlayers?: Array<typeof player>;
  caseInsensitiveExactPlayers?: Array<typeof player>;
  partialPlayers?: Array<typeof player>;
  topdeckPlayer?: typeof player | null;
  opponentName?: string;
  nameQueries?: string[];
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
        if (column === "name" && typeof values === "string") {
          options.nameQueries?.push(values);
          state.exactNameQuery = !(values.startsWith("%") && values.endsWith("%"));
          state.nameLookup = "ilike";
        }
        return query;
      },
      eq: (column: string, values: unknown) => {
        state.filters.push({ column, values });
        if (column === "name") {
          state.exactNameQuery = true;
          state.nameLookup = "eq";
        }
        return query;
      },
      in: (column: string, values: unknown[]) => {
        state.filters.push({ column, values });
        return query;
      },
      limit: () => query,
      maybeSingle: () => {
        state.expectSingle = true;
        return query;
      },
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
          if (table === "players" && filter("topdeck_id")) {
            data = options.topdeckPlayer === null
              ? []
              : [options.topdeckPlayer ?? player];
          } else if (table === "players" && !filter("id")) {
            data = state.nameLookup === "eq"
              ? options.exactPlayers ??
                (options.exactPlayer === null ? [] : [options.exactPlayer ?? player])
              : state.exactNameQuery
                ? options.caseInsensitiveExactPlayers ?? []
                : options.partialPlayers ?? [player];
          } else if (table === "tournament_entries" && filter("player_id")) {
            const range = state.range ?? [0, 999];
            options.entryRanges?.push([range[0], range[1]]);
            const entryCount = options.entryCount ?? 1;
            data = Array.from(
              { length: Math.max(0, Math.min(entryCount - range[0], range[1] - range[0] + 1)) },
              (_, index) => ({
                id: `entry-${range[0] + index + 1}`,
                player_id: options.topdeckPlayer?.id ?? player.id,
                tournament_id: "tournament-1",
                decklist_text: "decklist",
                decklist_url: null,
              })
            );
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
            options.gameBatches?.push(gameIds.length);
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
              name:
                options.opponentName ??
                `Opponent ${id.replace("opponent-player-", "")}`,
              topdeck_id: `${id}-topdeck`,
            }));
          }

          return Promise.resolve(
            onFulfilled({ data: state.expectSingle ? data[0] ?? null : data, error: null })
          );
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

  it.each([
    ["detailed", exportPlayerMatchups],
    ["summary", exportMatchupSummary],
  ] as const)(
    "pages the player's own participant history for %s exports",
    async (_label, exporter) => {
      const ownRanges: Array<[number, number]> = [];
      const gameBatches: number[] = [];
      const entryRanges: Array<[number, number]> = [];
      configureSupabaseMock({ ownRanges, gameBatches, entryRanges });

      const result = await exporter("Player One", "ranking");

      expect(ownRanges).toEqual([
        [0, 999],
        [1000, 1999],
      ]);
      expect(entryRanges).toEqual([[0, 999]]);
      expect(gameBatches).toEqual([200, 200, 200, 200, 200, 1]);
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

    await expect(exporter("Player One", "ranking")).rejects.toThrow(
      "game_participants query failed"
    );
  });

  it("prefers an exact player-name match", async () => {
    const ownRanges: Array<[number, number]> = [];
    const gameBatches: number[] = [];
    configureSupabaseMock({
      ownRanges,
      gameBatches,
      partialPlayers: [
        player,
        {
          ...player,
          id: "player-2",
          name: "Player One Alt",
        },
      ],
    });

    const result = await exportPlayerMatchups("Player One", "ranking");

    expect(JSON.parse(result ?? "[]")[0].player).toBe("Player One");
  });

  it("prefers a case-insensitive exact player-name match", async () => {
    configureSupabaseMock({
      ownRanges: [],
      exactPlayer: null,
      exactPlayers: [],
      caseInsensitiveExactPlayers: [player],
      partialPlayers: [
        player,
        {
          ...player,
          id: "player-2",
          name: "Player One Alt",
        },
      ],
    });

    const result = await exportPlayerMatchups("player one", "ranking");

    expect(JSON.parse(result ?? "[]")[0].player).toBe("Player One");
  });

  it("escapes LIKE metacharacters in exact and partial player-name lookups", async () => {
    const exactNameQueries: string[] = [];
    const specialPlayer = { ...player, name: "Player_One" };
    configureSupabaseMock({
      ownRanges: [],
      exactPlayer: null,
      exactPlayers: [],
      caseInsensitiveExactPlayers: [specialPlayer],
      partialPlayers: [specialPlayer],
      nameQueries: exactNameQueries,
    });

    await exportPlayerMatchups("player_one", "ranking");

    expect(exactNameQueries).toContain("player\\_one");

    const partialNameQueries: string[] = [];
    configureSupabaseMock({
      ownRanges: [],
      exactPlayer: null,
      exactPlayers: [],
      partialPlayers: [specialPlayer],
      nameQueries: partialNameQueries,
    });

    await exportPlayerMatchups("Player%", "ranking");

    expect(partialNameQueries).toContain("%Player\\%%");
  });

  it("uses the selected TopDeck ID instead of resolving the name again", async () => {
    const selectedPlayer = { ...player, id: "player-2", name: "Player One Alt" };
    configureSupabaseMock({
      ownRanges: [],
      topdeckPlayer: selectedPlayer,
      exactPlayers: [player],
      partialPlayers: [player],
    });

    const result = await exportPlayerMatchups("Player One", "ranking", "selected-topdeck-id");

    expect(JSON.parse(result ?? "[]")[0].player).toBe("Player One Alt");
  });

  it.each([
    exportPlayerMatchups,
    exportMatchupSummary,
  ])("rejects ambiguous partial player-name matches", async (exporter) => {
    configureSupabaseMock({
      ownRanges: [],
      exactPlayer: null,
      partialPlayers: [
        player,
        {
          ...player,
          id: "player-2",
          name: "Player One Alt",
        },
      ],
    });

    await expect(exporter("Player", "ranking")).rejects.toThrow(
      'Multiple players matched "Player"'
    );
  });

  it.each([exportPlayerMatchups, exportMatchupSummary])(
    "rejects duplicate exact player-name matches",
    async (exporter) => {
      configureSupabaseMock({
        ownRanges: [],
        exactPlayers: [
          player,
          {
            ...player,
            id: "player-2",
            topdeck_id: "player-2-topdeck-id",
          },
        ],
      });

      await expect(exporter("Player One", "ranking")).rejects.toThrow(
        'Multiple players matched "Player One"'
      );
    }
  );

  it("preserves opponent names containing pipe characters in summaries", async () => {
    configureSupabaseMock({
      ownRanges: [],
      opponentName: "Opponent | Pipe",
    });

    const result = await exportMatchupSummary("Player One", "ranking");
    const [summary] = JSON.parse(result ?? "[]");

    expect(summary.opponent).toBe("Opponent | Pipe");
    expect(summary.opponent_topdeck_id).toBe("opponent-player-0-topdeck");
  });

  it.each([exportPlayerMatchups, exportMatchupSummary])(
    "pages the player's tournament entries for %s exports",
    async (_exporter) => {
      const ownRanges: Array<[number, number]> = [];
      const entryRanges: Array<[number, number]> = [];
      configureSupabaseMock({
        ownRanges,
        entryRanges,
        entryCount: 1001,
      });

      await _exporter("Player One", "ranking");

      expect(entryRanges).toEqual([
        [0, 999],
        [1000, 1999],
      ]);
    }
  );
});
