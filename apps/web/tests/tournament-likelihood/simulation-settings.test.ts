import { describe, expect, it } from "vitest";
import { parseSimulationSettings } from "@/lib/simulation-settings";
const defaults = { swissRounds: 4, topCut: 16, runSeconds: 600, dropAfterRound: null, dropMinPoints: null };
const input = { swissRounds: "4", topCut: "16", runSeconds: "600", dropAfterRound: "", dropMinPoints: "" };
describe("simulation settings", () => {
  it("preserves explicit no-cut requests", () => {
    expect(parseSimulationSettings({ ...input, topCut: "0" }, defaults).topCut).toBe(0);
  });
  it.each(["-1", "1.5", "Infinity", "NaN"])("rejects invalid structure value %s", (topCut) => {
    expect(() => parseSimulationSettings({ ...input, topCut }, defaults)).toThrow();
    expect(() => parseSimulationSettings({ ...input, swissRounds: topCut }, defaults)).toThrow();
  });
  it("rejects invalid and partial drop rules", () => {
    expect(() => parseSimulationSettings({ ...input, dropAfterRound: "2" }, defaults)).toThrow();
    expect(() => parseSimulationSettings({ ...input, dropAfterRound: "5", dropMinPoints: "3" }, defaults)).toThrow();
  });
  it("captures a run independently of later edits", () => {
    const editable = { ...input };
    const submitted = parseSimulationSettings(editable, defaults);
    editable.topCut = "40";
    expect(submitted.topCut).toBe(16);
  });
});
