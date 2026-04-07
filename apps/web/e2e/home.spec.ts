import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("loads and displays hero section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /cEDH Analytics/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /competitive Commander analytics/i })).toBeVisible();
  });

  test("displays top commanders list with real data", async ({ page }) => {
    await expect(page.getByText("Commander performance")).toBeVisible();

    // Should have at least one commander link
    await page.waitForTimeout(2000);
    const commanderLinks = page.locator('a[href^="/commanders/"]');
    const count = await commanderLinks.count();
    expect(count).toBeGreaterThan(0);
  });

  test("displays top 3 popular commanders widget when data loads", async ({ page }) => {
    await expect(page.getByTestId("top-popular-commanders")).toBeVisible();
    await expect(page.getByText("Top 3 most popular commanders")).toBeVisible();

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

    await expect(rising.getByText("Biggest popularity gain (2 weeks)")).toBeVisible();
    const risingLinks = rising.locator('a[href^="/commanders/"]');
    const n = await risingLinks.count();
    expect(n).toBeGreaterThanOrEqual(1);
    expect(n).toBeLessThanOrEqual(3);
  });

  test("feature cards link to correct pages", async ({ page }) => {
    // Prefer the feature card link (not the nav link)
    const survivalCard = page.getByRole("link", { name: /Survival Analysis/i }).first();
    await expect(survivalCard).toBeVisible();

    // Click and verify navigation
    await survivalCard.click();
    await expect(page).toHaveURL(/\/survival/);
  });

  test("tool links on home are valid when present", async ({ page }) => {
    const optionalToolPaths = [
      "/tournament-likelihood",
      "/regional-elo",
    ];

    for (const path of optionalToolPaths) {
      const link = page.locator(`a[href="${path}"]`).first();
      if ((await link.count()) > 0) {
        await expect(link).toBeVisible();
      }
    }
  });
});
