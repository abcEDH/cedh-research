import { test, expect } from "@playwright/test";

test.describe("Commanders List Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/commanders");
  });

  test("loads and displays page title", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Commander Rankings/i })).toBeVisible();
  });

  test("displays the art-forward grid and can switch to the table", async ({ page }) => {
    const grid = page.getByTestId("commanders-grid");
    await expect(grid).toBeVisible();
    await expect(grid.locator("a").first()).toBeVisible();

    await page.getByRole("button", { name: "Table" }).click();
    const rankingsTable = page.getByTestId("all-commanders-table");
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
    await page.getByRole("button", { name: "Table" }).click();
    const rankingsTable = page.getByTestId("all-commanders-table");
    const rows = rankingsTable.locator("tbody tr");
    const rowCount = await rows.count();

    expect(rowCount).toBeGreaterThan(0);

    // First commander should have entries > 0
    const firstRowEntries = rows.first().locator("td").nth(2);
    const entriesText = await firstRowEntries.textContent();
    const entries = parseInt(entriesText?.replace(/,/g, "") || "0");
    expect(entries).toBeGreaterThan(0);
  });

  test("commander links navigate to detail page", async ({ page }) => {
    const commanderLinks = page.locator('a[href^="/commanders/"]');
    const total = await commanderLinks.count();
    let targetHref: string | null = null;
    for (let i = 0; i < total; i++) {
      const link = commanderLinks.nth(i);
      const href = await link.getAttribute("href");
      if (href && /\/commanders\/[a-f0-9-]+$/.test(href)) {
        targetHref = href;
        break;
      }
    }
    expect(targetHref).toBeTruthy();

    await page.goto(targetHref!);
    await expect(page).toHaveURL(/\/commanders\/[a-f0-9-]+/);
  });

  test("search and color filters are available", async ({ page }) => {
    await expect(page.getByRole("textbox", { name: "Search commanders" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Filter by Blue" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Most played" })).toBeVisible();
  });

  test("stats summary shows aggregated data", async ({ page }) => {
    await expect(page.getByText(/Total Commanders/i)).toBeVisible();
    await expect(page.getByText("Total Entries", { exact: true })).toBeVisible();

    const totalCommanders = page.getByTestId("stat-total-commanders");
    const totalEntries = page.getByTestId("stat-total-entries");

    const commanderCount = parseInt((await totalCommanders.textContent())?.replace(/,/g, "").trim() || "0", 10);
    const entryCount = parseInt((await totalEntries.textContent())?.replace(/,/g, "").trim() || "0", 10);

    expect(commanderCount).toBeGreaterThan(0);
    expect(entryCount).toBeGreaterThan(0);
  });
});
