import { test, devices } from "@playwright/test";

/**
 * Visual-review screenshot pass. Not part of the normal suite — it only
 * runs when SCREENSHOTS=1 is set, and it captures every key route at a
 * phone and a tablet viewport into ./screenshots/ (gitignored) for
 * attaching to a PR.
 *
 *   SCREENSHOTS=1 npx playwright test screenshots --project=chromium
 *
 * Uses the chromium project's browser but overrides the viewport per
 * capture, so it does not depend on the mobile projects being installed.
 */
const ROUTES = [
  "/",
  "/tournaments",
  "/commanders",
  "/regional-elo",
  "/tournament-likelihood",
  "/trap-spice",
  "/about",
];

const VIEWPORTS = [
  { label: "phone", ...devices["iPhone 14"].viewport },
  { label: "tablet", width: 768, height: 1024 },
];

test.describe("Visual review screenshots", () => {
  test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to capture");

  for (const vp of VIEWPORTS) {
    for (const path of ROUTES) {
      test(`${vp.label} ${path}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        const slug = path === "/" ? "home" : path.replace(/\//g, "_").replace(/^_/, "");
        await page.screenshot({
          path: `screenshots/${vp.label}-${slug}.png`,
          fullPage: true,
        });
      });
    }
  }
});
