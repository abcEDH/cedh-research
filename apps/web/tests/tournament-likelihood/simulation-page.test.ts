import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
vi.mock("@/lib/topdeck", () => ({
  extractTournamentSlug: () => "small-event",
  fetchTournamentBySlug: vi.fn(async () => ({ data: { name: "Small Event" }, standings: Array(16).fill({}) })),
  defaultTournamentStructureForPlayerCount: () => ({ swissRounds: 6, topCut: 40 }),
  fetchTournamentStructureDefaults: vi.fn(async () => ({ swissRounds: 2, topCut: 0, source: "event_page" })),
}));
vi.mock("@/app/tournament-likelihood/simulate/simulation-runner", () => ({
  SimulationRunner: (props: Record<string, unknown>) => React.createElement("div", null, `rounds=${props.defaultSwissRounds};cut=${props.defaultTopCut}`),
}));
import Page from "@/app/tournament-likelihood/simulate/page";
describe("simulation page defaults", () => {
  it("uses the inferred structure instead of fixed six/forty defaults", async () => {
    const html = renderToStaticMarkup(await Page({ searchParams: { tournament: "small-event" } }));
    expect(html).toContain("rounds=2;cut=0");
  });
  it("keeps explicit valid overrides", async () => {
    const html = renderToStaticMarkup(await Page({ searchParams: { tournament: "small-event", swissRounds: "4", topCut: "16" } }));
    expect(html).toContain("rounds=4;cut=16");
  });
});
