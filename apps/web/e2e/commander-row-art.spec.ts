import { test, expect } from "@playwright/test";
import { expectNoHorizontalOverflow } from "./helpers/overflow";

// These surfaces require populated Supabase data, like the player-profile E2E
// suite. Mock only Scryfall so artwork always loads without external rate limits.
for (const path of ["/", "/regional-elo/player/10XZGpOw5vVlD7VeYRO1XvBv3Ft2"]) {
  test(`commander artwork stays inside its cell on ${path}`, async ({ page }, testInfo) => {
    test.setTimeout(90_000);
    await page.route("https://api.scryfall.com/cards/named?*", (route) =>
      route.fulfill({ json: { image_uris: { art_crop: "https://cards.scryfall.io/test-art.svg" } } })
    );
    await page.route("https://cards.scryfall.io/test-art.svg", (route) =>
      route.fulfill({
        contentType: "image/svg+xml",
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="#447799"/></svg>',
      })
    );
    await page.goto(path);
    const backdrop = page.getByTestId("commander-row-backdrop").first();
    await backdrop.scrollIntoViewIfNeeded();
    await expect(backdrop.locator("img")).toBeVisible();
    await expect.poll(() => backdrop.locator("img").evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);

    async function expectContained() {
      const bounds = await backdrop.evaluate((element) => {
        const image = element.querySelector("img")!;
        const cell = element.closest("td")!;
        const row = cell.closest("tr")!;
        return {
          image: image.getBoundingClientRect().toJSON(),
          cell: cell.getBoundingClientRect().toJSON(),
          row: row.getBoundingClientRect().toJSON(),
        };
      });
      expect(bounds.image.height).toBeGreaterThan(0);
      for (const container of [bounds.cell, bounds.row]) {
        expect(bounds.image.top).toBeGreaterThanOrEqual(container.top - 1);
        expect(bounds.image.bottom).toBeLessThanOrEqual(container.bottom + 1);
        expect(bounds.image.left).toBeGreaterThanOrEqual(container.left - 1);
        expect(bounds.image.right).toBeLessThanOrEqual(container.right + 1);
      }
      // The decorative layer must not intercept the cell's link.
      await backdrop.locator("..").locator("a").first().click({ trial: true });
      await expectNoHorizontalOverflow(page);
    }

    await expectContained();
    await testInfo.attach("contained-artwork", { body: await page.screenshot(), contentType: "image/png" });
    await page.evaluate(() => window.scrollBy(0, 150));
    await expectContained();
    await page.setViewportSize({ width: 320, height: 740 });
    await backdrop.scrollIntoViewIfNeeded();
    await expectContained();
  });
}
