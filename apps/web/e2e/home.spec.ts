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

  test("feature cards link to correct pages", async ({ page }) => {
    // Prefer the feature card link (not the nav link)
    const survivalCard = page.getByRole("link", { name: /Survival Analysis/i }).first();
    await expect(survivalCard).toBeVisible();

    // Click and verify navigation
    await survivalCard.click();
    await expect(page).toHaveURL(/\/survival/);
  });

  test("new tools are discoverable from home", async ({ page }) => {
    expect(await page.locator('a[href="/tournament-likelihood"]').count()).toBeGreaterThan(0);
    expect(await page.locator('a[href="/midseason-invitational"]').count()).toBeGreaterThan(0);
    expect(await page.locator('a[href="/regional-elo"]').count()).toBeGreaterThan(0);
  });
});
