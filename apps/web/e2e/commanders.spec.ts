import { test, expect } from "@playwright/test";

test.describe("Commanders List Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/commanders");
  });

  test("loads and displays page title", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Commander Rankings/i })).toBeVisible();
  });

  test("displays commanders table with data", async ({ page }) => {
    // Table should be visible
    await expect(page.locator("table")).toBeVisible();

    // Should have table headers
    await expect(page.getByRole("columnheader", { name: /Rank/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Commander/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Entries/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Win Rate/i })).toBeVisible();
  });

  test("commanders have non-zero entry counts", async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(2000);

    // Get entry counts from table
    const rows = page.locator("tbody tr");
    const rowCount = await rows.count();

    expect(rowCount).toBeGreaterThan(0);

    // First commander should have entries > 0
    const firstRowEntries = rows.first().locator("td").nth(2);
    const entriesText = await firstRowEntries.textContent();
    const entries = parseInt(entriesText?.replace(/,/g, "") || "0");
    expect(entries).toBeGreaterThan(0);
  });

  test("commander links navigate to detail page", async ({ page }) => {
    // Click first commander
    const firstCommander = page.locator('a[href^="/commanders/"]').first();
    await firstCommander.click();

    // Should navigate to commander detail page
    await expect(page).toHaveURL(/\/commanders\/[a-f0-9-]+/);
  });

  test("stats summary shows aggregated data", async ({ page }) => {
    // Should show total commanders count
    await expect(page.getByText(/Total Commanders/i)).toBeVisible();

    // Should show total entries
    await expect(page.getByText(/Total Entries/i)).toBeVisible();

    // Values should not be 0 - look for the value with font-mono class
    const totalEntriesValue = page.locator("text=Total Entries").locator("..").locator("p.font-mono");
    await expect(totalEntriesValue).not.toHaveText("0");
  });
});
