import { test, expect } from "@playwright/test";
import { expectNoHorizontalOverflow } from "./helpers/overflow";

test.describe("Installability", () => {
  test("manifest is linked and served with icons", async ({ page, request }) => {
    await page.goto("/");
    const manifestHref = await page
      .locator('link[rel="manifest"]')
      .getAttribute("href");
    expect(manifestHref).toBeTruthy();

    const res = await request.get(manifestHref!);
    expect(res.status()).toBe(200);
    const manifest = await res.json();
    expect(manifest.name).toBe("tedh.gg");
    expect(manifest.display).toBe("standalone");
    expect(manifest.icons.length).toBeGreaterThanOrEqual(3);
  });

  test("apple touch icon is linked", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveCount(1);
  });
});

test.describe("Mobile navigation", () => {
  test.skip(({ isMobile }) => !isMobile, "mobile viewports only");

  test("hamburger opens drawer with all nav links and closes on navigation", async ({
    page,
  }) => {
    await page.goto("/");

    const trigger = page.getByRole("button", { name: /open navigation menu/i });
    await expect(trigger).toBeVisible();

    await trigger.click();
    const drawer = page.getByRole("dialog");
    await expect(drawer).toBeVisible();
    for (const label of [
      "Tournaments",
      "Commanders",
      "Leaderboard",
      "Tournament Prep",
      "Methodology",
    ]) {
      await expect(drawer.getByRole("link", { name: label })).toBeVisible();
    }

    await drawer.getByRole("link", { name: "Tournaments" }).click();
    await page.waitForURL("**/tournaments");
    await expect(drawer).not.toBeVisible();
  });

  test("desktop nav pills are hidden on mobile", async ({ page }) => {
    await page.goto("/");
    const header = page.locator("header");
    await expect(
      header.locator("nav").getByRole("link", { name: "Tournaments" })
    ).toBeHidden();
  });
});

test.describe("No horizontal overflow", () => {
  test.skip(({ isMobile }) => !isMobile, "mobile viewports only");

  for (const path of ["/", "/tournaments", "/commanders", "/regional-elo"]) {
    test(`${path} fits the viewport`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoHorizontalOverflow(page);
    });
  }
});
