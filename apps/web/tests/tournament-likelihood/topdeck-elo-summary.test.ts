import { describe, expect, it } from "vitest";
import {
  buildTopdeckEloSummary,
  DEFAULT_MISSING_TOPDECK_ELO,
} from "@/app/tournament-likelihood/topdeck-elo-summary";

describe("buildTopdeckEloSummary", () => {
  it("averages published TopDeck Elo values", () => {
    const summary = buildTopdeckEloSummary(
      ["player-1", "player-2"],
      new Map([
        ["player-1", 1600],
        ["player-2", 1800],
      ])
    );

    expect(summary.average).toBe(1700);
    expect(summary.publishedCount).toBe(2);
    expect(summary.missingCount).toBe(0);
    expect(summary.totalPlayers).toBe(2);
  });

  it("uses 1500 for attendees without published TopDeck Elo", () => {
    const summary = buildTopdeckEloSummary(
      ["player-1", "player-2", "player-3"],
      new Map([["player-1", 1800]])
    );

    expect(summary.average).toBe((1800 + 1500 + 1500) / 3);
    expect(summary.defaultElo).toBe(DEFAULT_MISSING_TOPDECK_ELO);
    expect(summary.publishedCount).toBe(1);
    expect(summary.missingCount).toBe(2);
  });

  it("counts duplicate attendee rows independently", () => {
    const summary = buildTopdeckEloSummary(
      ["player-1", "player-1", "player-2"],
      new Map([["player-1", 1700]])
    );

    expect(summary.average).toBe((1700 + 1700 + 1500) / 3);
    expect(summary.publishedCount).toBe(2);
    expect(summary.missingCount).toBe(1);
  });

  it("returns null average when there are no attendees", () => {
    const summary = buildTopdeckEloSummary([], new Map());

    expect(summary.average).toBeNull();
    expect(summary.totalPlayers).toBe(0);
  });
});
