import { describe, expect, it, vi } from "vitest";
vi.mock("@/lib/supabase", () => ({ supabase: {} }));
import { buildProfiles, type CommanderUsageRow } from "@/lib/meta-prep";

describe("commander forecast fallback", () => {
  it("matches the persisted 75% recency / 25% latest-deck model", () => {
    const entry = (commander_name: string, start_date: string): CommanderUsageRow => ({
      topdeck_id: "janos", player_name: "Janos", commander_name, start_date,
      wins: 0, draws: 0, losses: 0, player_count: 32,
      decklist_url: null, topdeck_decklist_url: null,
    });
    const result = buildProfiles(["janos"], [
      entry("Scion", "2026-09-19T00:00:00Z"),
      entry("Tymna / Thrasios", "2026-10-18T00:00:00Z"),
    ], 3, "2026-10-24T00:00:00Z");
    const predictions = result.players[0].commanders;
    const scionWeight = 0.5 ** (35 / 24);
    const latestWeight = 0.5 ** (6 / 24);
    expect(predictions[0].commander).toBe("Tymna / Thrasios");
    expect(predictions[0].predictionShare).toBeCloseTo(0.25 + 0.75 * latestWeight / (scionWeight + latestWeight));
    expect(predictions[1].predictionShare).toBeCloseTo(0.75 * scionWeight / (scionWeight + latestWeight));
    expect(predictions.reduce((sum, row) => sum + row.predictionShare, 0)).toBeCloseTo(1);
    expect(predictions[0].entries).toBe(1);
    expect(predictions[0].latestDate).toBe("2026-10-18T00:00:00Z");
  });
  it("ranks the latest deck first when its bonus overtakes repeated older choices", () => {
    const entry = (commander_name: string, start_date: string): CommanderUsageRow => ({
      topdeck_id: "player", player_name: "Player", commander_name, start_date,
      wins: 0, draws: 0, losses: 0, player_count: 32,
      decklist_url: null, topdeck_decklist_url: null,
    });
    const result = buildProfiles(["player"], [
      entry("Older deck", "2026-10-22T00:00:00Z"),
      entry("Older deck", "2026-10-23T00:00:00Z"),
      entry("Latest deck", "2026-10-24T00:00:00Z"),
    ], 1, "2026-10-25T00:00:00Z");
    expect(result.players[0].commanders).toHaveLength(1);
    expect(result.players[0].commanders[0].commander).toBe("Latest deck");
    expect(result.players[0].commanders[0].predictionShare).toBeGreaterThan(0.5);
    expect(result.players[0].totalEntries).toBe(3);
  });

});
