import { describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({
  unstable_cache: (fn: (...args: unknown[]) => unknown) => {
    const cache = new Map();
    return (...args: unknown[]) => {
      const key = JSON.stringify(args);
      if (!cache.has(key)) cache.set(key, fn(...args));
      return cache.get(key);
    };
  },
}));
vi.mock("@/lib/topdeck", () => ({ fetchTournamentBySlug: vi.fn() }));
vi.mock("@/lib/supabase", () => ({ supabase: { from: () => ({ select: () => ({ in: async () => ({ data: [], error: null }) }) }) } }));
vi.mock("@/lib/meta-prep", () => ({
  COMMANDER_FALLBACK_LOOKBACK_MONTHS: 12,
  getCommanderDecklistRows: vi.fn(async () => []),
  getCommanderUsageRows: vi.fn(async () => []),
  selectCommanderForecastRows: () => [],
  buildProfiles: () => ({ players: [], metaShare: [] }),
  attachLatestDecklistUrls: (value: unknown) => value,
  lookbackStartDate: () => "2026-01-01",
}));
import { fetchTournamentBySlug } from "@/lib/topdeck";
import { getCommanderDecklistRows } from "@/lib/meta-prep";
import { getTournamentAnalysis } from "@/app/tournament-likelihood/tournament-analysis";

describe("live standings with cached historical forecasts", () => {
  it("updates ranks, points and results without reloading unchanged deck histories", async () => {
    const standing = { id: "player", name: "Player", standing: 5, points: 0, wins: 0, draws: 0, losses: 1, actualDeckCommander: null, actualDecklistUrl: null };
    const initial = { data: { name: "Event", startDate: 1, game: "Magic", format: "EDH" }, standings: [standing], rounds: [], standingsAvailable: true };
    vi.mocked(fetchTournamentBySlug).mockResolvedValueOnce(initial).mockResolvedValueOnce({
      ...initial, standings: [{ ...standing, standing: 1, points: 5, wins: 1 }], rounds: [{ tables: [] }],
    });
    expect((await getTournamentAnalysis("example", 6)).standings[0].standing).toBe(5);
    const refreshed = await getTournamentAnalysis("example", 6);
    expect(refreshed.standings[0]).toMatchObject({ standing: 1, points: 5, wins: 1, losses: 1 });
    expect(refreshed.hasRounds).toBe(true);
    expect(refreshed.standingsAvailable).toBe(true);
    expect(fetchTournamentBySlug).toHaveBeenCalledTimes(2);
    expect(getCommanderDecklistRows).toHaveBeenCalledTimes(1);
  });
});
