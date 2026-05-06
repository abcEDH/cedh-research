import { describe, expect, it } from "vitest";
import {
  aggregateTrendPoint,
  formatPercent,
  mean,
} from "@/lib/commander-stats";

describe("commander-stats helpers", () => {
  describe("mean", () => {
    it("returns null for an empty array", () => {
      expect(mean([])).toBeNull();
    });

    it("returns null when every value is non-finite", () => {
      expect(mean([NaN, Infinity, -Infinity])).toBeNull();
    });

    it("ignores NaN values produced by parseFloat(null)", () => {
      // parseFloat(null as never) === NaN — this mirrors how commander_stats
      // rows expose null avg_win_rate values from Postgres.
      const winRates = [0.2, 0.3, parseFloat(null as unknown as string), 0.4];
      expect(mean(winRates)).toBeCloseTo(0.3, 6);
    });

    it("computes the average over finite entries", () => {
      expect(mean([1, 2, 3, 4])).toBe(2.5);
    });
  });

  describe("formatPercent", () => {
    it("renders an em-dash when the value is null", () => {
      expect(formatPercent(null)).toBe("—");
    });

    it("formats a decimal as a one-place percentage", () => {
      expect(formatPercent(0.2296)).toBe("23.0%");
    });

    it("never returns NaN% when given NaN", () => {
      expect(formatPercent(NaN)).toBe("—");
    });
  });

  describe("aggregateTrendPoint", () => {
    it("returns null win rate and points/game for periods with no games", () => {
      // Real-world Jan 2026 shape: ~4500 entries logged but per-round games
      // not yet ingested (wins/losses/draws all zero).
      const result = aggregateTrendPoint({
        entries: 4490,
        wins: 0,
        losses: 0,
        draws: 0,
      });
      expect(result.entries).toBe(4490);
      expect(result.winRate).toBeNull();
      expect(result.pointsPerGame).toBeNull();
    });

    it("computes win rate as a percentage and points/game from results", () => {
      const result = aggregateTrendPoint({
        entries: 12,
        wins: 5,
        losses: 6,
        draws: 1,
      });
      expect(result.entries).toBe(12);
      expect(result.winRate).toBeCloseTo((5 / 12) * 100, 6);
      expect(result.pointsPerGame).toBeCloseTo((5 * 5 + 1) / 12, 6);
    });
  });
});
