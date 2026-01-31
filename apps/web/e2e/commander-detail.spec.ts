import { test, expect } from "@playwright/test";

test.describe("Commander Detail Page", () => {
  // Use a known popular commander - we'll find one from the commanders list
  let commanderId: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await page.goto("/commanders");

    // Get the first commander's link to extract ID
    const firstCommanderLink = page.locator('a[href^="/commanders/"]').first();
    const href = await firstCommanderLink.getAttribute("href");
    commanderId = href?.replace("/commanders/", "") || "";
    await page.close();
  });

  test("loads commander page with stats", async ({ page }) => {
    test.skip(!commanderId, "No commander ID found");

    await page.goto(`/commanders/${commanderId}`);

    // Should show commander name
    const heading = page.locator("h1");
    await expect(heading).toBeVisible();

    // Should show performance stats
    await expect(page.getByText(/Win Rate/i).first()).toBeVisible();
    await expect(page.getByText(/Entries/i).first()).toBeVisible();
  });

  test("displays matchups section with real data", async ({ page }) => {
    test.skip(!commanderId, "No commander ID found");

    await page.goto(`/commanders/${commanderId}`);

    // Wait for matchups to load
    await page.waitForTimeout(2000);

    // Should have matchups section
    const matchupsSection = page.getByText(/Matchups/i).first();
    await expect(matchupsSection).toBeVisible();

    // Matchup data should have non-zero values
    // Look for game counts that aren't "0 games"
    const matchupRows = page.locator("text=/\\d+ games/i");
    const count = await matchupRows.count();

    if (count > 0) {
      // At least one matchup should have games > 0
      const firstMatchup = await matchupRows.first().textContent();
      expect(firstMatchup).not.toBe("0 games");
    }
  });

  test("matchup win rates are not all zero", async ({ page }) => {
    test.skip(!commanderId, "No commander ID found");

    await page.goto(`/commanders/${commanderId}`);
    await page.waitForTimeout(3000);

    // Look for win rate percentages in matchups
    // They should not all be 0.0%
    const winRates = page.locator("text=/\\d+\\.\\d+% WR/i");
    const count = await winRates.count();

    if (count > 0) {
      let hasNonZeroWinRate = false;
      for (let i = 0; i < Math.min(count, 5); i++) {
        const text = await winRates.nth(i).textContent();
        if (text && !text.includes("0.0%")) {
          hasNonZeroWinRate = true;
          break;
        }
      }
      expect(hasNonZeroWinRate).toBe(true);
    }
  });

  test("notable players section displays", async ({ page }) => {
    test.skip(!commanderId, "No commander ID found");

    await page.goto(`/commanders/${commanderId}`);

    // Should have notable players section
    await expect(page.getByText(/Notable Players/i)).toBeVisible({ timeout: 10000 });
  });

  test("player links go to TopDeck.gg profiles", async ({ page }) => {
    test.skip(!commanderId, "No commander ID found");

    await page.goto(`/commanders/${commanderId}`);
    await page.waitForTimeout(2000);

    // Look for external links to topdeck.gg
    const topdeckLinks = page.locator('a[href*="topdeck.gg/profile"]');
    const count = await topdeckLinks.count();

    // If there are players with topdeck_id, they should link correctly
    if (count > 0) {
      const href = await topdeckLinks.first().getAttribute("href");
      expect(href).toContain("topdeck.gg/profile/");
      expect(href).not.toContain("null");
    }
  });
});
