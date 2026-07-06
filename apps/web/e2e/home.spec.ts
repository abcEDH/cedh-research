import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("loads and displays hero section", async ({ page }) => {
    await expect(page.getByRole("link", { name: /tedh\.gg/i }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /competitive Intelligence for cEDH/i })).toBeVisible();
  });

  test("displays global leaderboard table with internal links", async ({ page, isMobile }) => {
    await expect(page.getByText("Global Leaderboard")).toBeVisible();
    await expect(page.getByRole("link", { name: "Full View" })).toHaveAttribute(
      "href",
      "/regional-elo"
    );

    const leaderboardTable = page.getByTestId("global-leaderboard-table");
    await expect(leaderboardTable).toBeVisible();
    await expect(leaderboardTable.getByRole("columnheader", { name: "Elo" }).first()).toBeVisible();
    // The Commander column is dropped below the sm: breakpoint (column priority).
    const commanderHeader = leaderboardTable.getByRole("columnheader", { name: "Commander" }).first();
    if (isMobile) {
      await expect(commanderHeader).toBeHidden();
    } else {
      await expect(commanderHeader).toBeVisible();
    }

    const playerLinks = leaderboardTable.locator('a[href^="/regional-elo/player/"]');
    const playerLinkCount = await playerLinks.count();
    if (playerLinkCount > 0) {
      await expect(playerLinks.first()).toBeVisible();
    } else {
      await expect(page.getByTestId("global-leaderboard-empty")).toBeVisible();
    }
    await expect(page.locator('a[href="https://topdeck.gg/elo/magic-the-gathering/edh"]')).toHaveCount(0);
  });

  test("displays top commanders list with real data", async ({ page }) => {
    await expect(page.getByText("Field Performance")).toBeVisible();

    // Should have at least one commander link
    await page.waitForTimeout(2000);
    const commanderLinks = page.locator('a[href^="/commanders/"]');
    const count = await commanderLinks.count();
    expect(count).toBeGreaterThan(0);
  });

  test("displays top 3 popular commanders widget when data loads", async ({ page }) => {
    await expect(page.getByTestId("top-popular-commanders")).toBeVisible();
    await expect(page.getByText("Most Popular Commanders")).toBeVisible();

    await page.waitForTimeout(2000);
    const widgetLinks = page.getByTestId("top-popular-commanders").locator('a[href^="/commanders/"]');
    const widgetCommanderCount = await widgetLinks.count();
    expect(widgetCommanderCount).toBeGreaterThanOrEqual(1);
    expect(widgetCommanderCount).toBeLessThanOrEqual(3);
  });

  test("displays rising popularity widget when positive 2-week deltas exist", async ({ page }) => {
    await page.waitForTimeout(2000);
    const rising = page.getByTestId("top-rising-commanders");
    if ((await rising.count()) === 0) return;

    await expect(rising.getByText("Rising Stars")).toBeVisible();
    const risingLinks = rising.locator('a[href^="/commanders/"]');
    const n = await risingLinks.count();
    expect(n).toBeGreaterThanOrEqual(1);
    expect(n).toBeLessThanOrEqual(3);
  });

  test("displays prominent tournament prep section", async ({ page }) => {
    await expect(page.locator('div[data-slot="card-title"]:has-text("Tournament Prep")')).toBeVisible();
    const runSimulatorBtn = page.getByRole("link", { name: /Run Simulator/i });
    await expect(runSimulatorBtn).toBeVisible();
    await runSimulatorBtn.click();
    await expect(page).toHaveURL(/\/tournament-likelihood/);
  });

  test("navigation links are valid", async ({ page, isMobile }) => {
    const navPaths = [
      "/tournament-likelihood",
      "/regional-elo",
      "/commanders",
      "/about",
    ];

    if (isMobile) {
      // Mobile keeps the nav links in the hamburger drawer, not the header row.
      await page.getByRole("button", { name: /open navigation menu/i }).click();
      const drawer = page.getByRole("dialog");
      for (const path of navPaths) {
        await expect(drawer.locator(`a[href="${path}"]`).first()).toBeVisible();
      }
    } else {
      for (const path of navPaths) {
        const link = page.locator(`header nav a[href="${path}"]`).first();
        await expect(link).toBeVisible();
      }
    }
  });
});
