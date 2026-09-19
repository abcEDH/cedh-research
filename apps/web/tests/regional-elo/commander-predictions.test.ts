import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CommanderPredictions } from "@/components/commander-predictions";
import { commanderPredictionRows, type PlayerCommanderProfileRow } from "@/lib/commander-predictions";

function profile(shares: number[]): PlayerCommanderProfileRow {
  return { active_commander: "A", active_commander_prediction_score: 3,
    latest_commander: "B", latest_commander_date: null,
    commander_predictions: shares.map((share, i) => ({ commander: String.fromCharCode(65 + i), entries: 3, prediction_share: share, model_share: 3 })) };
}

describe("commander prediction shares", () => {
  it("renders normalized shares even when legacy raw weights exceed one", () => {
    const html = renderToStaticMarkup(React.createElement(CommanderPredictions, { profile: profile([0.6, 0.3, 0.1]) }));
    expect(html).toContain("60.0%");
    expect(html).not.toContain("300.0%");
    expect(commanderPredictionRows(profile([0.6, 0.3, 0.1])).reduce((sum, row) => sum + (row.share ?? 0), 0)).toBeCloseTo(1);
  });
  it("preserves missing probability mass outside the top three", () => {
    expect(commanderPredictionRows(profile([0.4, 0.3, 0.2, 0.1])).reduce((sum, row) => sum + (row.share ?? 0), 0)).toBeCloseTo(0.9);
  });
  it("does not format missing or invalid normalized shares as percentages", () => {
    const value = profile([3, -1, Number.NaN]);
    expect(commanderPredictionRows(value).every((row) => row.share === null)).toBe(true);
    value.commander_predictions![0].prediction_share = undefined;
    expect(commanderPredictionRows(value)[0].share).toBeNull();
  });
});
