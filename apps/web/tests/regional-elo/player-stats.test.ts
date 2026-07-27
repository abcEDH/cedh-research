import { describe, expect, it } from "vitest";

import {
  filterPlayerLogs,
  summarizePlayerLogs,
  type PlayerGameLog,
} from "@/app/regional-elo/player/[topdeckId]/player-stats";

describe("summarizePlayerLogs", () => {
  it("builds consistent totals, seat summaries, and opponent records", () => {
    const logs: PlayerGameLog[] = [
      {
        gameId: "game-1",
        startDate: "2026-04-01",
        tournamentName: "Regional Open",
        state: "California",
        roundLabel: "Round 1",
        tableLabel: "Table 1",
        seat: 1,
        result: "win",
        commanderName: "Rograkh / Silas",
        opponents: [
          {
            topdeckId: "opp-a",
            playerName: "Opponent A",
            commanderName: "Blue Farm",
            seat: 2,
            result: "loss",
          },
          {
            topdeckId: "opp-b",
            playerName: "Opponent B",
            commanderName: "Nadu",
            seat: 3,
            result: "loss",
          },
        ],
      },
      {
        gameId: "game-2",
        startDate: "2026-04-02",
        tournamentName: "Regional Open",
        state: "California",
        roundLabel: "Round 2",
        tableLabel: "Table 2",
        seat: 2,
        result: "loss",
        commanderName: "Rograkh / Silas",
        opponents: [
          {
            topdeckId: "opp-a",
            playerName: "Opponent A",
            commanderName: "Blue Farm",
            seat: 1,
            result: "win",
          },
          {
            topdeckId: "opp-c",
            playerName: "Opponent C",
            commanderName: "Kinnan",
            seat: 4,
            result: "loss",
          },
        ],
      },
      {
        gameId: "game-3",
        startDate: "2026-04-03",
        tournamentName: "Regional Open",
        state: "California",
        roundLabel: "Round 3",
        tableLabel: "Table 3",
        seat: 4,
        result: "draw",
        commanderName: "Rograkh / Silas",
        opponents: [
          {
            topdeckId: "opp-b",
            playerName: "Opponent B",
            commanderName: "Nadu",
            seat: 2,
            result: "draw",
          },
        ],
      },
    ];

    const summary = summarizePlayerLogs(logs);

    expect(summary.totalGames).toBe(3);
    expect(summary.totalWins).toBe(1);
    expect(summary.totalLosses).toBe(1);
    expect(summary.totalDraws).toBe(1);

    expect(summary.seatRows).toEqual([
      { seat: 1, games: 1, wins: 1, draws: 0, losses: 0 },
      { seat: 2, games: 1, wins: 0, draws: 0, losses: 1 },
      { seat: 3, games: 0, wins: 0, draws: 0, losses: 0 },
      { seat: 4, games: 1, wins: 0, draws: 1, losses: 0 },
    ]);

    expect(summary.opponentRecords).toEqual([
      {
        opponentTopdeckId: "opp-a",
        opponentName: "Opponent A",
        wins: 1,
        draws: 0,
        losses: 1,
        games: 2,
      },
      {
        opponentTopdeckId: "opp-b",
        opponentName: "Opponent B",
        wins: 1,
        draws: 1,
        losses: 0,
        games: 2,
      },
      {
        opponentTopdeckId: "opp-c",
        opponentName: "Opponent C",
        wins: 0,
        draws: 0,
        losses: 1,
        games: 1,
      },
    ]);
  });

  it("filters aggregate logs to 30-player events without changing Elo data", () => {
    const logs: PlayerGameLog[] = [
      { gameId: "large", result: "win", tournamentPlayerCount: 30 } as PlayerGameLog,
      { gameId: "small", result: "win", tournamentPlayerCount: 30, rankingEligible: false } as PlayerGameLog,
      { gameId: "unknown", result: "win", tournamentPlayerCount: null } as PlayerGameLog,
      { gameId: "bye", result: "bye" } as PlayerGameLog,
    ];

    expect(filterPlayerLogs(logs, false).map((log) => log.gameId)).toEqual([
      "large",
      "small",
      "unknown",
    ]);
    expect(filterPlayerLogs(logs, true).map((log) => log.gameId)).toEqual(["large"]);
  });

  it("keeps displayed game totals equal to W-L-D totals when byes are present", () => {
    const logs: PlayerGameLog[] = [
      {
        gameId: "win",
        result: "win",
        seat: 1,
        opponents: [],
      } as PlayerGameLog,
      {
        gameId: "bye",
        result: "bye",
        seat: 1,
        opponents: [],
      } as PlayerGameLog,
      {
        gameId: "draw",
        result: "draw",
        seat: 1,
        opponents: [],
      } as PlayerGameLog,
    ];

    const summary = summarizePlayerLogs(filterPlayerLogs(logs, false));

    expect(summary.totalGames).toBe(2);
    expect(summary.totalWins + summary.totalDraws + summary.totalLosses).toBe(
      summary.totalGames
    );
  });
});
