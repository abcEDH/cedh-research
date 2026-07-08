import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("loads and displays hero section", async ({ page }) => {
    await expect(page.getByRole("link", { name: /tedh\.gg/i }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /competitive Intelligence for cEDH/i })).toBeVisible();
  });

  test("displays global leaderboard table with internal links", async ({ page }) => {
    await expect(page.getByText("Global Leaderboard")).toBeVisible();
    await expect(page.getByRole("link", { name: "Full View" })).toHaveAttribute(
      "href",
      "/regional-elo"
    );

    const leaderboardTable = page.getByTestId("global-leaderboard-table");
    await expect(leaderboardTable).toBeVisible();
    await expect(leaderboardTable.getByRole("columnheader", { name: "Elo" }).first()).toBeVisible();
    await expect(leaderboardTable.getByRole("columnheader", { name: "Commander" }).first()).toBeVisible();

    const playerLinks = leaderboardTable.locator('a[href^="/regional-elo/player/"]');
    const playerLinkCount = await playerLinks.count();
    if (playerLinkCount > 0) {
      await expect(playerLinks.first()).toBeVisible();
    } else {
      await expect(page.getByTestId("global-leaderboard-empty")).toBeVisible();
    }
    await expect(page.locator('a[href="https://topdeck.gg/elo/magic-the-gathering/edh"]')).toHaveCount(0);
  });

  test("does not display removed commander/win-rate sections", async ({ page }) => {
    await expect(page.getByText("Field Performance")).toHaveCount(0);
    await expect(page.getByText("Win Rate Leaders")).toHaveCount(0);
    await expect(page.getByText("Most Popular Commanders")).toHaveCount(0);
    await expect(page.getByText("Rising Stars")).toHaveCount(0);
    await expect(page.getByTestId("top-popular-commanders")).toHaveCount(0);
    await expect(page.getByTestId("top-rising-commanders")).toHaveCount(0);
  });

  test("displays prominent tournament prep section", async ({ page }) => {
    await expect(page.locator('div[data-slot="card-title"]:has-text("Tournament Prep")')).toBeVisible();
    const runSimulatorBtn = page.getByRole("link", { name: /Run Simulator/i });
    await expect(runSimulatorBtn).toBeVisible();
    await runSimulatorBtn.click();
    await expect(page).toHaveURL(/\/tournament-likelihood/);
  });

  test("navigation links are valid", async ({ page }) => {
    const navPaths = [
      "/tournament-likelihood",
      "/regional-elo",
      "/commanders",
      "/about",
    ];

    for (const path of navPaths) {
      const link = page.locator(`header nav a[href="${path}"]`).first();
      await expect(link).toBeVisible();
    }
  });
});
