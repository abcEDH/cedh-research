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
    // Check survival analysis link exists (it's a CardTitle, not a heading)
    const survivalCard = page.locator('a[href="/survival"]');
    await expect(survivalCard).toBeVisible();

    // Click and verify navigation
    await survivalCard.click();
    await expect(page).toHaveURL(/\/survival/);
  });

  test("new tools are discoverable from home", async ({ page }) => {
    await expect(page.locator('a[href="/tournament-likelihood"]')).toBeVisible();
    await expect(page.locator('a[href="/midseason-invitational"]')).toBeVisible();
    await expect(page.locator('a[href="/regional-elo"]')).toBeVisible();
  });
});
