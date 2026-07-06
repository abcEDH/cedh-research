import { describe, expect, it } from "vitest";
import {
  computeMetaShare,
  formatPercent,
  formatWinRate,
  totalEntries,
} from "@/lib/archetypes/stats";
import { formatDate, formatRecord, winRateFromWLD } from "@/lib/tournaments/stats";

describe("archetype stats", () => {
  it("sums total entries", () => {
    expect(totalEntries([{ entries: 3 }, { entries: 7 }])).toBe(10);
    expect(totalEntries([])).toBe(0);
  });

  it("computes meta share as a fraction of total entries", () => {
    const rows = computeMetaShare([{ entries: 30 }, { entries: 10 }]);
    expect(rows[0].metaShare).toBeCloseTo(0.75);
    expect(rows[1].metaShare).toBeCloseTo(0.25);
    expect(rows.reduce((sum, row) => sum + row.metaShare, 0)).toBeCloseTo(1);
  });

  it("returns zero shares when there are no entries", () => {
    const rows = computeMetaShare([{ entries: 0 }, { entries: 0 }]);
    expect(rows.every((row) => row.metaShare === 0)).toBe(true);
  });

  it("formats win rates, using an em dash for unknowns", () => {
    expect(formatWinRate(0.5)).toBe("50.0%");
    expect(formatWinRate(0)).toBe("0.0%");
    expect(formatWinRate(null)).toBe("—");
    expect(formatWinRate(undefined)).toBe("—");
    expect(formatWinRate(Number.NaN)).toBe("—");
  });

  it("formats percentages", () => {
    expect(formatPercent(0.1234)).toBe("12.3%");
    expect(formatPercent(0.1234, 0)).toBe("12%");
  });
});

describe("tournament stats", () => {
  it("computes win rate from W/L/D", () => {
    expect(winRateFromWLD(3, 1, 0)).toBeCloseTo(0.75);
    expect(winRateFromWLD(2, 1, 1)).toBeCloseTo(0.5);
    expect(winRateFromWLD(0, 0, 0)).toBeNull();
    expect(winRateFromWLD(null, null, null)).toBeNull();
    expect(winRateFromWLD(2, null, null)).toBe(1);
  });

  it("formats W/L/D records tolerating nulls", () => {
    expect(formatRecord(3, 1, 0)).toBe("3-1-0");
    expect(formatRecord(null, null, null)).toBe("0-0-0");
  });

  it("formats dates in UTC with an em dash for unknowns", () => {
    expect(formatDate("2026-05-17T00:00:00Z")).toBe("May 17, 2026");
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("—");
  });
});
