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
    expect(source).toContain('console.info(`[regional-player] ${event}`, details);');
    expect(source).toContain('logPlayerReadSummary("tournament-entries-cache-miss"');
    expect(source).toContain("return buildPlayerAchievements(rows, topdeckId);");
    expect(source).toContain("return buildPlayerCommanderUsageRows(rows, topdeckId, playerName);");
  });

  it("uses materialized active leaderboard Elo fields for displayed ranks and TopDeck Elo", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/regional-elo/player/[topdeckId]/page.tsx"),
      "utf-8"
    );

    expect(source).toContain("last_game_date, topdeck_elo, topdeck_elo_rank");
    expect(source).toContain("row.topdeck_elo_rank ?? row.rank");
    expect(source).toContain("const displayedTopdeckElo");
    expect(source).not.toContain("fetchActiveDisplayedRank");
    expect(source).not.toContain('.from("topdeck_player_elos")');
    expect(source).not.toContain("fetchTopdeckElo(topdeckId)");
  });
});
