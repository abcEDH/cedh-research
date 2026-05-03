import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href, ...props }, children),
}));

vi.mock("next/cache", () => ({
  unstable_cache: <T extends (...args: never[]) => unknown>(callback: T) => callback,
}));

vi.mock("server-only", () => ({}));

vi.mock("@/lib/supabase", () => {
  const mockRows = [
    {
      commander_id: "cmd-1",
      commander_name: "Tymna / Kraum",
      archetype: null,
      color_identity: ["W", "U", "B", "R"],
      total_entries: 100,
      tournaments_played: 20,
      total_wins: 40,
      total_losses: 50,
      total_draws: 10,
      avg_win_rate: "0.4",
      top_16_count: 10,
      conversion_rate_top_16: "0.1",
      top_cut_count: 5,
      conversion_rate_top_cut: "0.05",
    },
  ];

  const weeklyRows = [
    {
      commander_id: "cmd-1",
      week_key: "2026-W01",
      week_start_date: "2026-01-05",
      entries: 12,
      wins: 5,
      losses: 6,
      draws: 1,
      total_players: 64,
    },
  ];

  const monthlyRows = [
    {
      commander_id: "cmd-1",
      month_key: "2026-01",
      entries: 30,
      wins: 12,
      losses: 15,
      draws: 3,
      total_players: 120,
    },
  ];

  function createMockQuery(table: string) {
    const chain = {
      select: () => chain,
      gt: () => chain,
      not: () => chain,
      order: () => chain,
      in: () => chain,
      range: () => chain,
      then: (
        onfulfilled?: ((value: { data: unknown; error: null }) => unknown) | null
      ) => {
        let data: unknown;
        if (table === "commander_stats") {
          data = mockRows;
        } else if (table === "commander_weekly_trends") {
          data = weeklyRows;
        } else if (table === "commander_monthly_trends") {
          data = monthlyRows;
        } else {
          data = [];
        }
        return Promise.resolve({ data, error: null }).then(onfulfilled);
      },
    };
    return chain;
  }

  return {
    supabase: {
      from: (table: string) => createMockQuery(table),
    },
  };
});

// Mock UI components to avoid importing complex component trees
vi.mock("@/components/commanders/commanders-table", () => ({
  default: () => React.createElement("div", { "data-testid": "commanders-table" }),
}));

vi.mock("@/components/commanders/commander-trends-table", () => ({
  default: () => React.createElement("div", { "data-testid": "commander-trends-table" }),
  // Re-export the type as an empty object for the named export
}));

vi.mock("@/components/commanders/trend-metric-charts", () => ({
  default: () => React.createElement("div", { "data-testid": "trend-metric-charts" }),
}));

vi.mock("@/components/ui/card", () => ({
  Card: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "card" }, children),
  CardContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  CardHeader: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  CardTitle: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
}));

vi.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  TooltipTrigger: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  TooltipContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
}));

describe("Commanders page caching", () => {
  it("exports COMMANDERS_CACHE_REVALIDATE_SECONDS equal to 1800 (30 minutes)", async () => {
    // The constant is module-scoped but not exported, so we verify it indirectly
    // by checking the module can be imported and the constant value is correct.
    // We read it from the source to confirm the value.
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/commanders/page.tsx"),
      "utf-8"
    );
    const match = source.match(
      /const COMMANDERS_CACHE_REVALIDATE_SECONDS\s*=\s*(.+?);/
    );
    expect(match).not.toBeNull();
    // Evaluate the expression (60 * 30 = 1800)
    expect(eval(match![1])).toBe(1800);
  });

  it("module imports without errors and default export is a function", async () => {
    const pageModule = await import("@/app/commanders/page");
    expect(pageModule).toBeDefined();
    expect(typeof pageModule.default).toBe("function");
  });

  it("renders the synchronous page shell without throwing", async () => {
    const pageModule = await import("@/app/commanders/page");
    const element = await pageModule.default();
    const html = renderToStaticMarkup(element);

    // The heading and navigation render synchronously; data-driven
    // sections are wrapped in <Suspense> so renderToStaticMarkup
    // shows their fallbacks rather than the resolved content.
    expect(html).toContain("Commander Rankings");
    expect(html).toContain("Back to Home");
    expect(html).toContain("View commander trends");
  });

  it("source contains all four cached wrapper definitions with expected cache keys", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/commanders/page.tsx"),
      "utf-8"
    );

    expect(source).toContain('getCachedCommanders = unstable_cache(');
    expect(source).toContain('["commanders-list-v1"]');

    expect(source).toContain('getCachedCommanderPeriodSnapshots = unstable_cache(');
    expect(source).toContain('["commander-period-snapshots-v1"]');

    expect(source).toContain('getCachedWeeklyEntries = unstable_cache(');
    expect(source).toContain('["commander-weekly-entries-v1"]');

    expect(source).toContain('getCachedGlobalTrendSeries = unstable_cache(');
    expect(source).toContain('["commander-global-trends-v3"]');
  });

  it("page module calls cached wrappers instead of raw functions", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/commanders/page.tsx"),
      "utf-8"
    );

    // Strip the cached wrapper definitions before checking for raw calls,
    // since the cached wrappers themselves legitimately call the raw fns.
    const sourceWithoutCachedDefs = source.replace(
      /unstable_cache\([\s\S]*?\)/g,
      "unstable_cache(/* stripped */)"
    );

    // Cached wrappers must be invoked somewhere in the module.
    expect(sourceWithoutCachedDefs).toMatch(/getCachedCommanders\(\)/);
    expect(sourceWithoutCachedDefs).toMatch(/getCachedCommanderPeriodSnapshots\(/);
    expect(sourceWithoutCachedDefs).toMatch(/getCachedWeeklyEntries\(/);
    expect(sourceWithoutCachedDefs).toMatch(/getCachedGlobalTrendSeries\(\)/);

    // Raw functions must never be awaited outside their cached wrappers.
    expect(sourceWithoutCachedDefs).not.toMatch(/\bawait getCommanders\(\)/);
    expect(sourceWithoutCachedDefs).not.toMatch(/\bawait getCommanderPeriodSnapshots\(/);
    expect(sourceWithoutCachedDefs).not.toMatch(/\bawait getWeeklyEntries\(/);
    expect(sourceWithoutCachedDefs).not.toMatch(/\bawait getGlobalTrendSeries\(\)/);
  });

  it("source throws on fetch errors instead of caching fallback empties", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/commanders/page.tsx"),
      "utf-8"
    );

    expect(source).toContain("throw error;");
    expect(source).toContain("throw weeklyFallback.error;");
    expect(source).toContain("throw monthlyFallback.error;");
    expect(source).not.toContain('console.error("Error fetching commanders:", error);\n    return [];');
    expect(source).not.toContain('console.error("Error fetching weekly trends:", error);\n    return {};');
  });

  it("canonicalizes top commander IDs before cached snapshot lookups", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../src/app/commanders/page.tsx"),
      "utf-8"
    );

    expect(source).toContain("const topCommanderIds = topCommanders");
    expect(source).toContain(".sort((a, b) => a.localeCompare(b))");
    expect(source).toContain("getCachedCommanderPeriodSnapshots(topCommanderIds)");
    expect(source).toContain("getCachedWeeklyEntries(topCommanderIds, 12)");
  });
});
