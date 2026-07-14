import { expect, type Page } from "@playwright/test";

/**
 * Asserts the page does not scroll horizontally at the current viewport.
 * The +1 tolerates subpixel rounding differences between engines.
 */
export async function expectNoHorizontalOverflow(page: Page) {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(
    scrollWidth,
    `page scrolls horizontally: scrollWidth ${scrollWidth} > viewport ${innerWidth}`
  ).toBeLessThanOrEqual(innerWidth + 1);
}
