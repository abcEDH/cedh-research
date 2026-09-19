import { describe, expect, it } from "vitest";
import { buildProfilesFromPrecomputedRows } from "@/app/tournament-likelihood/precomputed-profiles";

describe("buildProfilesFromPrecomputedRows", () => {
  it("uses model_share when available", () => {
    const profiles = buildProfilesFromPrecomputedRows(["player-1"], [
      {
        topdeck_id: "player-1",
        player_name: "Player One",
        total_entries: 2,
        commander_predictions: [
          {
            commander: "Commander A",
            entries: 1,
            prediction_score: 0.6,
            prediction_share: 0.6,
            model_share: 0.4,
            latest_date: "2026-01-01",
            latest_decklist_url: null,
          },
          {
            commander: "Commander B",
            entries: 1,
            prediction_score: 0.4,
            prediction_share: 0.4,
            model_share: 0.6,
            latest_date: "2026-02-01",
            latest_decklist_url: null,
          },
        ],
      },
    ]);

    expect(profiles?.players[0].commanders[0].predictionShare).toBe(0.4);
    expect(profiles?.players[0].commanders[1].predictionShare).toBe(0.6);
    expect(profiles?.metaShare.map((row) => [row.commander, row.entries])).toEqual([
      ["Commander B", 0.6],
      ["Commander A", 0.4],
    ]);
  });

  it("falls back to prediction_share for older precomputed rows", () => {
    const profiles = buildProfilesFromPrecomputedRows(["player-1"], [
      {
        topdeck_id: "player-1",
        player_name: "Player One",
        total_entries: 1,
        commander_predictions: [
          {
            commander: "Commander A",
            entries: 1,
            prediction_score: 0.7,
            prediction_share: 0.7,
            latest_date: "2026-01-01",
            latest_decklist_url: null,
          },
        ],
      },
    ]);

    expect(profiles?.players[0].commanders[0].predictionShare).toBe(0.7);
    expect(profiles?.metaShare[0]).toMatchObject({
      commander: "Commander A",
      entries: 0.7,
      share: 1,
    });
  });
});
