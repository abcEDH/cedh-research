import { describe, it, expect } from "vitest";
import type { WinrateMatrixRow, CommanderMetaEv } from "@/lib/schemas/api-contracts";
import type { CommanderLabel } from "@/lib/winrates/fetchers";
import {
  classifyWinrateHeat,
  HEAT_BG_CLASS,
  formatPercent,
  formatCiRange,
  formatSampleSize,
  cellKey,
  buildRowBundles,
  sortRowBundles,
  parseDaysBack,
  DEFAULT_DAYS_BACK,
} from "@/lib/winrates/stats";

const COMMANDERS: CommanderLabel[] = [
  { id: "aaaaaaaa-0000-0000-0000-000000000001", name: "Alpha" },
  { id: "bbbbbbbb-0000-0000-0000-000000000002", name: "Beta" },
  { id: "cccccccc-0000-0000-0000-000000000003", name: "Gamma" },
];

function matrixRow(overrides: Partial<WinrateMatrixRow>): WinrateMatrixRow {
  return {
    deck_a_commander_id: COMMANDERS[0].id,
    deck_b_commander_id: null,
    games_played: 100,
    wins: 50,
    losses: 50,
    draws: 0,
    point_winrate: 0.5,
    ci_low: 0.4038,
    ci_high: 0.5962,
    ...overrides,
  };
}

// A mocked get_winrate_matrix response for 3 top-N commanders: each has an OVERALL row plus a
// mirror cell and pairwise cells against the other two.
const MOCK_RPC_RESPONSE: WinrateMatrixRow[] = [
  matrixRow({ deck_a_commander_id: COMMANDERS[0].id, deck_b_commander_id: null, games_played: 300, wins: 90, point_winrate: 0.3 }),
  matrixRow({ deck_a_commander_id: COMMANDERS[0].id, deck_b_commander_id: COMMANDERS[0].id, games_played: 300, wins: 150, point_winrate: 0.5 }),
  matrixRow({ deck_a_commander_id: COMMANDERS[0].id, deck_b_commander_id: COMMANDERS[1].id, games_played: 10, wins: 2, point_winrate: 0.2 }),
  matrixRow({ deck_a_commander_id: COMMANDERS[0].id, deck_b_commander_id: COMMANDERS[2].id, games_played: 60, wins: 36, point_winrate: 0.6 }),

  matrixRow({ deck_a_commander_id: COMMANDERS[1].id, deck_b_commander_id: null, games_played: 200, wins: 80, point_winrate: 0.4 }),
  matrixRow({ deck_a_commander_id: COMMANDERS[1].id, deck_b_commander_id: COMMANDERS[1].id, games_played: 200, wins: 100, point_winrate: 0.5 }),
  matrixRow({ deck_a_commander_id: COMMANDERS[1].id, deck_b_commander_id: COMMANDERS[0].id, games_played: 10, wins: 8, point_winrate: 0.8 }),

  matrixRow({ deck_a_commander_id: COMMANDERS[2].id, deck_b_commander_id: null, games_played: 100, wins: 55, point_winrate: 0.55 }),
  matrixRow({ deck_a_commander_id: COMMANDERS[2].id, deck_b_commander_id: COMMANDERS[2].id, games_played: 100, wins: 50, point_winrate: 0.5 }),
];

const MOCK_EV_RESPONSE: CommanderMetaEv[] = [
  {
    commander_id: COMMANDERS[0].id,
    meta_ev: 0.28,
    meta_ev_ci_low: 0.22,
    meta_ev_ci_high: 0.34,
    composition_coverage: 0.7,
    pods_present: 300,
    is_statistically_significant: true,
  },
  {
    commander_id: COMMANDERS[1].id,
    meta_ev: 0.41,
    meta_ev_ci_low: 0.35,
    meta_ev_ci_high: 0.47,
    composition_coverage: 0.9,
    pods_present: 200,
    is_statistically_significant: true,
  },
  // commander 2 deliberately has no EV row -- exercises the "missing EV" render path.
];

describe("classifyWinrateHeat", () => {
  it.each([
    [0.0, "cold"],
    [0.29, "cold"],
    [0.3, "cool"],
    [0.49, "cool"],
    [0.5, "warm"],
    [0.59, "warm"],
    [0.6, "hot"],
    [1.0, "hot"],
  ] as const)("classifies %f as %s", (winrate, expected) => {
    expect(classifyWinrateHeat(winrate)).toBe(expected);
  });

  it("gives every bucket a distinct background class", () => {
    const classes = new Set(Object.values(HEAT_BG_CLASS));
    expect(classes.size).toBe(4);
  });
});

describe("formatting helpers", () => {
  it("formats percentages with no decimals by default", () => {
    expect(formatPercent(0.5)).toBe("50%");
    expect(formatPercent(0.3333, 1)).toBe("33.3%");
  });

  it("formats a null/undefined value as an em dash", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatPercent(undefined)).toBe("—");
  });

  it("formats a CI range as low–high text", () => {
    expect(formatCiRange(0.4038, 0.5962)).toBe("40%–60%");
  });

  it("formats a missing CI as an em dash", () => {
    expect(formatCiRange(null, null)).toBe("—");
  });

  it("pluralizes sample size correctly", () => {
    expect(formatSampleSize(1)).toBe("1 match");
    expect(formatSampleSize(843)).toBe("843 matches");
  });

  it("builds a stable cell key, normalizing null to the OVERALL sentinel", () => {
    expect(cellKey("a", "b")).toBe("a:b");
    expect(cellKey("a", null)).toBe("a:OVERALL");
  });
});

describe("buildRowBundles", () => {
  const bundles = buildRowBundles(COMMANDERS, MOCK_RPC_RESPONSE, MOCK_EV_RESPONSE);

  it("renders exactly one bundle per top-N commander (expected row count)", () => {
    expect(bundles).toHaveLength(3);
  });

  it("gives each row the expected number of opponent cells, including the mirror cell", () => {
    const alpha = bundles.find((b) => b.commander.id === COMMANDERS[0].id)!;
    // mirror (self) + 2 opponents = 3 cells total in this fixture.
    expect(alpha.cellsByOpponent.size).toBe(3);
    expect(alpha.cellsByOpponent.get(COMMANDERS[0].id)?.point_winrate).toBe(0.5); // mirror = 50%
  });

  it("attaches the OVERALL row and EV row to the right commander", () => {
    const beta = bundles.find((b) => b.commander.id === COMMANDERS[1].id)!;
    expect(beta.overall?.games_played).toBe(200);
    expect(beta.ev?.meta_ev).toBe(0.41);
  });

  it("tolerates a commander with no EV row instead of throwing", () => {
    const gamma = bundles.find((b) => b.commander.id === COMMANDERS[2].id)!;
    expect(gamma.ev).toBeNull();
  });
});

describe("sortRowBundles", () => {
  const bundles = buildRowBundles(COMMANDERS, MOCK_RPC_RESPONSE, MOCK_EV_RESPONSE);

  it("sorts by number of matches (OVERALL games_played), descending by default", () => {
    const sorted = sortRowBundles(bundles, "matches", "desc");
    expect(sorted.map((b) => b.commander.name)).toEqual(["Alpha", "Beta", "Gamma"]);
  });

  it("reverses to ascending", () => {
    const sorted = sortRowBundles(bundles, "matches", "asc");
    expect(sorted.map((b) => b.commander.name)).toEqual(["Gamma", "Beta", "Alpha"]);
  });

  it("sorts by OVERALL winrate", () => {
    const sorted = sortRowBundles(bundles, "winrate", "desc");
    expect(sorted.map((b) => b.commander.name)).toEqual(["Gamma", "Beta", "Alpha"]);
  });

  it("sorts by meta EV, treating a missing EV as lowest", () => {
    const sorted = sortRowBundles(bundles, "ev", "desc");
    expect(sorted.map((b) => b.commander.name)).toEqual(["Beta", "Alpha", "Gamma"]);
  });

  it("sorts alphabetically", () => {
    const sorted = sortRowBundles(bundles, "alphabetical", "asc");
    expect(sorted.map((b) => b.commander.name)).toEqual(["Alpha", "Beta", "Gamma"]);
  });

  it("does not mutate the input array", () => {
    const originalOrder = bundles.map((b) => b.commander.id);
    sortRowBundles(bundles, "winrate", "asc");
    expect(bundles.map((b) => b.commander.id)).toEqual(originalOrder);
  });
});

describe("parseDaysBack", () => {
  it("accepts an allowed value", () => {
    expect(parseDaysBack("60")).toBe(60);
  });

  it("falls back to the default for an unknown value", () => {
    expect(parseDaysBack("999")).toBe(DEFAULT_DAYS_BACK);
    expect(parseDaysBack(undefined)).toBe(DEFAULT_DAYS_BACK);
  });

  it("takes the first value when given an array (repeated search param)", () => {
    expect(parseDaysBack(["30", "15"])).toBe(30);
  });
});
