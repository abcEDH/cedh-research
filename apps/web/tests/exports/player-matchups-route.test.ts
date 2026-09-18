import { describe, expect, it } from "vitest";
import { buildMatchupExportFilenames } from "@/app/api/export/player-matchups/route";

describe("buildMatchupExportFilenames", () => {
  it("distinguishes summary exports from detailed exports", () => {
    const detailed = buildMatchupExportFilenames("Player One", "ranking", false);
    const summary = buildMatchupExportFilenames("Player One", "ranking", true);

    expect(detailed.encodedFileName).toContain("Player_One_ranking_matchups.json");
    expect(summary.encodedFileName).toContain("Player_One_ranking_matchups_summary.json");
    expect(summary.encodedFileName).not.toBe(detailed.encodedFileName);
  });
});
