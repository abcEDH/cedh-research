import { describe, expect, it } from "vitest";
import { isEloTierEligible, parseEloTier } from "@/lib/elo-tiers";

const tournament = {
  name: "Major cEDH Open",
  topdeck_tid: "major-cedh-open",
  player_count: 64,
  start_date: "2026-07-01T00:00:00Z",
};

describe("ELO tier eligibility", () => {
  it("defaults unknown tier values to ranking", () => {
    expect(parseEloTier("unexpected")).toBe("ranking");
    expect(parseEloTier("all")).toBe("all");
  });

  it("uses tournament and game rules for ranking eligibility", () => {
    expect(isEloTierEligible("ranking", tournament)).toBe(true);
    expect(isEloTierEligible("ranking", { ...tournament, player_count: 29 })).toBe(false);
  });

  it("allows decklist-free local events once they reach ten players", () => {
    expect(isEloTierEligible("local", { ...tournament, player_count: 10 })).toBe(true);
    expect(isEloTierEligible("local", { ...tournament, player_count: 9 })).toBe(false);
  });

  it("excludes leagues from ranking but allows them in local", () => {
    expect(isEloTierEligible("ranking", { ...tournament, topdeck_tid: "spring-league" })).toBe(false);
    expect(isEloTierEligible("local", { ...tournament, topdeck_tid: "spring-league" })).toBe(true);
    expect(isEloTierEligible("local", { ...tournament, name: "Casual cEDH Night" })).toBe(false);
  });

  it("keeps dated games in the all-games tier", () => {
    expect(isEloTierEligible("all", tournament)).toBe(true);
    expect(isEloTierEligible("all", { ...tournament, start_date: null })).toBe(false);
  });
});
