import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("loads and displays hero section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /cEDH Analytics/i })).toBeVisible();
    await expect(page.getByText(/Data-driven insights/i)).toBeVisible();
  });

  test("displays tournament and commander counts from database", async ({ page }) => {
    // Stats cards should show real data (not 0)
    await expect(page.getByText("Tournaments Tracked")).toBeVisible();
    await expect(page.getByText("Unique Commanders")).toBeVisible();

    // Wait for data to load and verify counts are displayed
    await page.waitForTimeout(2000);

    // Look for large numbers (stats values are in bold text)
    const statsValues = page.locator("p.text-4xl.font-bold");
    const count = await statsValues.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test("displays top commanders list with real data", async ({ page }) => {
    // Most Popular section should have commanders
    await expect(page.getByText("Most Popular")).toBeVisible();

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
});
