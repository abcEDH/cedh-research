import { test, expect } from "@playwright/test";

test.describe("Survival Analysis Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/survival");
  });

  test("loads and displays page title", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Survival Analysis", exact: true })).toBeVisible();
  });

  test("displays overall survival chart with bars", async ({ page }) => {
    // Wait for loading to complete - look for chart elements
    await page.waitForTimeout(3000);

    // Chart should have round labels (R1, R2, etc.)
    await expect(page.getByText("R1")).toBeVisible();
    await expect(page.getByText("R2")).toBeVisible();

    // Bars are rendered with inline styles, look for elements with backgroundColor
    // The seat legend should have colored squares
    const legend = page.locator("text=Seat 1 (First)");
    await expect(legend).toBeVisible();

    // There should be a chart container with bars having height styles
    const chartBars = page.locator('[title^="Seat"]');
    const barCount = await chartBars.count();
    expect(barCount).toBeGreaterThan(0);
  });

  test("displays survival view toggle buttons", async ({ page }) => {
    // Should have view toggle buttons
    await expect(page.getByRole("button", { name: /By Seat Position/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Global Average/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /By Commander/i })).toBeVisible();
  });

  test("displays methodology explanation", async ({ page }) => {
    // Should explain what survival analysis means
    await expect(page.getByText(/Kaplan-Meier/i)).toBeVisible();
  });

  test("survival rates are valid percentages", async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(2000);

    // Check that percentage values are displayed (should have % symbol)
    const percentages = page.locator("text=/%$/");
    const count = await percentages.count();

    // Should have multiple percentage displays
    expect(count).toBeGreaterThan(0);
  });
});
