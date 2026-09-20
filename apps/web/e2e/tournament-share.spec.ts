import { expect, test } from "@playwright/test";

test("cleans mobile share text before submitting tournament prep", async ({ page }) => {
  await page.goto("/tournament-likelihood");
  const input = page.getByRole("textbox", { name: "TopDeck tournament link or slug" });
  await input.fill("previous-event");
  const url = "https://topdeck.gg/bracket/l7-summer-invitational-2026";
  await input.evaluate((element, sharedText) => {
    const clipboardData = new DataTransfer();
    clipboardData.setData("text/plain", sharedText);
    element.dispatchEvent(new ClipboardEvent("paste", { clipboardData, bubbles: true, cancelable: true }));
  }, `L7 Summer Invitational 2026\n${url}?utm_source=share\nJoin me on TopDeck!`);
  await expect(input).toHaveValue(url);

  // Inspect the form request without depending on a live TopDeck API response.
  await page.route("**/tournament-likelihood?*", (route) => route.fulfill({
    contentType: "text/html", body: "Tournament request received",
  }));
  await page.getByRole("button", { name: "Analyze Tournament" }).click();
  await expect(page).toHaveURL((value) => value.searchParams.get("tournament") === url);
});
