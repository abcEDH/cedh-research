import { describe, expect, it } from "vitest";

describe("regional player read path", () => {
  it("reuses one cached tournament_entries read for achievements and commander usage", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const componentsSource = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/regional-elo/player/[topdeckId]/player-profile-components.tsx"),
      "utf-8"
    );
    const pageSource = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/regional-elo/player/[topdeckId]/page.tsx"),
      "utf-8"
    );

    expect(componentsSource).toContain("async function fetchPlayerTournamentEntries");
    expect(componentsSource).toContain('console.info(`[regional-player] ${event}`, details);');
    expect(pageSource).toContain('console.info(`[regional-player] ${event}`, details);');
    expect(pageSource).toContain("function logPlayerReadSummary(");
    expect(componentsSource).toContain("async function fetchPlayerTournamentEntries");
    expect(componentsSource.match(/fetchPlayerTournamentEntries\(playerId\)/g)).toHaveLength(2);
  });

  it("uses materialized active leaderboard Elo fields for displayed ranks and TopDeck Elo", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/regional-elo/player/[topdeckId]/player-profile-components.tsx"),
      "utf-8"
    );

    expect(source).toContain("last_game_date, topdeck_elo, topdeck_elo_rank");
    expect(source).toContain("row.topdeck_elo_rank ?? row.rank");
    expect(source).toContain("const displayedTopdeckElo");
    expect(source).toContain('.from("global_elo_active_leaderboard")');
    expect(source).toContain('.from("global_elo_player_profile_summaries")');
    expect(source).toContain("fetchCachedPlayerCommanderProfile");
    expect(source).not.toContain("fetchActiveDisplayedRank");
    expect(source).not.toContain('.from("topdeck_player_elos")');
    expect(source).not.toContain('.from("global_elo_leaderboard")');
    expect(source).not.toContain('.from("regional_elo_leaderboard")');
    expect(source).not.toContain('.from("regional_elo_active_leaderboard")');
    expect(source).not.toContain('.from("regional_elo_player_profile_summaries")');
    expect(source).not.toContain("buildProfiles");
    expect(source).not.toContain("selectCommanderForecastRows");
    expect(source).not.toContain("fetchTopdeckElo(topdeckId)");
  });

  it("does not use a global leaderboard row as the country-rank fallback", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/regional-elo/player/[topdeckId]/player-profile-components.tsx"),
      "utf-8"
    );

    const countryRankSource = source.slice(
      source.indexOf("async function fetchCountryRank"),
      source.indexOf("async function fetchRegionalRanks")
    );

    expect(countryRankSource).toContain('fetchActiveRankRow("country", countryKey, playerId)');
    expect(countryRankSource).not.toContain('.eq("region_type", "global")');
    expect(countryRankSource).not.toContain('.eq("region_key", "ALL")');
  });
});
