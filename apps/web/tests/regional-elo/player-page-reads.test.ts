import { describe, expect, it } from "vitest";

describe("regional player read path", () => {
  it("reuses one cached tournament_entries read for achievements and commander usage", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/regional-elo/player/[topdeckId]/page.tsx"),
      "utf-8"
    );

    expect(source).toContain("async function fetchPlayerTournamentEntries");
    expect(source).toContain('[regional-player] tournament-entries-cache-miss');
    expect(source).toContain("return buildPlayerAchievements(rows, topdeckId);");
    expect(source).toContain("return buildPlayerCommanderUsageRows(rows, topdeckId, playerName);");
  });
});
