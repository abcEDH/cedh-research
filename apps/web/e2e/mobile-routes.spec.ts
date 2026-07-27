import { test } from "@playwright/test";
import { expectNoHorizontalOverflow } from "./helpers/overflow";

/**
 * Horizontal-overflow guard across every route that renders without live
 * data. Runs on the mobile projects only — the desktop viewport is wide
 * enough that overflow rarely reproduces there.
 *
 * Dynamic detail routes (/tournaments/[slug], /commanders/[id], a player
 * profile) are intentionally omitted: they need a real slug/id, which the
 * local Supabase stub does not provide. Cover those against a preview
 * deploy with BASE_URL set.
 */
const ROUTES = [
  "/",
  "/tournaments",
  "/commanders",
  "/commanders/trends",
  "/regional-elo",
  "/analytics/player-matchups",
  "/tournament-likelihood",
  "/trap-spice",
  "/about",
  "/limitations",
  "/methodology/elo",
  "/methodology/data-model",
];

test.describe("Mobile route overflow", () => {
  test.skip(({ isMobile }) => !isMobile, "mobile viewports only");

  for (const path of ROUTES) {
    test(`${path} has no horizontal overflow`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoHorizontalOverflow(page);
    });
  }
});
