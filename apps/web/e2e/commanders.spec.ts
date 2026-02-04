import { test, expect } from "@playwright/test";

test.describe("Commanders List Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/commanders");
  });

  test("loads and displays page title", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Commander Rankings/i })).toBeVisible();
  });

  test("displays commanders table with data", async ({ page }) => {
    // Primary rankings table should be visible
    const rankingsTable = page.locator("table").first();
    await expect(rankingsTable).toBeVisible();

    // Should have table headers
    await expect(rankingsTable.getByRole("columnheader", { name: /Rank/i }).first()).toBeVisible();
    await expect(rankingsTable.getByRole("columnheader", { name: /Commander/i }).first()).toBeVisible();
    await expect(
      rankingsTable.getByRole("columnheader", { name: /^Entries\b/i }).first(),
    ).toBeVisible();
    await expect(rankingsTable.getByRole("columnheader", { name: /Win Rate/i }).first()).toBeVisible();
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
    // Click first commander link whose href ends with UUID (avoid /commanders/trends)
    const commanderLinks = page.locator('a[href^="/commanders/"]');
    const total = await commanderLinks.count();
    let clicked = false;
    for (let i = 0; i < total; i++) {
      const link = commanderLinks.nth(i);
      const href = await link.getAttribute("href");
      if (href && /\/commanders\/[a-f0-9-]+$/.test(href)) {
        await link.click();
        clicked = true;
        break;
      }
    }
    expect(clicked).toBe(true);

    // Should navigate to commander detail page
    await expect(page).toHaveURL(/\/commanders\/[a-f0-9-]+/);
  });

  test("stats summary shows aggregated data", async ({ page }) => {
    // Should show total commanders count
    await expect(page.getByText(/Total Commanders/i)).toBeVisible();

    // Should show total entries
    await expect(page.getByText("Total Entries", { exact: true })).toBeVisible();

    // Values should not be 0
    const totalEntriesValue = page
      .locator("p", { hasText: "Total Entries" })
      .locator("xpath=../../p")
      .first();
    const text = (await totalEntriesValue.textContent()) ?? "";
    expect(text.replace(/,/g, "")).not.toBe("0");
  });
});
