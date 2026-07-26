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

  it("requires a non-empty decklist for ranking games", () => {
    expect(isEloTierEligible("ranking", tournament, { decklist_text: "1 Mana Crypt" })).toBe(true);
    expect(isEloTierEligible("ranking", tournament, { decklist_text: "  ", decklist_url: null })).toBe(false);
  });

  it("allows decklist-free local events once they reach ten players", () => {
    expect(isEloTierEligible("local", { ...tournament, player_count: 10 }, {})).toBe(true);
    expect(isEloTierEligible("local", { ...tournament, player_count: 9 }, {})).toBe(false);
  });

  it("excludes league and obvious casual events from filtered tiers", () => {
    expect(isEloTierEligible("ranking", { ...tournament, topdeck_tid: "spring-league" }, { decklist_url: "https://deck" })).toBe(false);
    expect(isEloTierEligible("local", { ...tournament, name: "Casual cEDH Night" }, {})).toBe(false);
  });

  it("keeps dated games in the all-games tier", () => {
    expect(isEloTierEligible("all", tournament, {})).toBe(true);
    expect(isEloTierEligible("all", { ...tournament, start_date: null }, {})).toBe(false);
  });
});
