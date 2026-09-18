# Mobile web checklist

Manual and automated checks for the mobile-web features. Run the automated
parts on every PR that touches layout; run the manual parts before a release
that changes installability or a data-heavy page.

## Automated (CI + local)

- `npm run test:e2e` runs the desktop and mobile Playwright projects. The
  mobile projects (`mobile-chrome` = Pixel 7, `mobile-safari` = iPhone 14)
  cover:
  - `e2e/mobile-shell.spec.ts` — nav drawer opens/closes, manifest + apple
    touch icon are linked, `/manifest.webmanifest` serves the icon set, and
    no horizontal overflow on the core routes.
  - `e2e/mobile-routes.spec.ts` — `expectNoHorizontalOverflow` across every
    route that renders without live data.
- `mobile-safari` needs WebKit installed (`npx playwright install webkit`);
  `mobile-chrome` runs on the bundled Chromium.
- Visual review: `SCREENSHOTS=1 npx playwright test screenshots --project=chromium`
  writes full-page phone + tablet captures to `screenshots/` (gitignored) to
  attach to a PR.

## Manual — installability (per release touching manifest/icons)

- Chrome DevTools → Application → Manifest: no warnings, "installable".
- Android Chrome / desktop Chrome: install prompt appears; installed icon,
  short name, and splash `background_color` (`#030915`) are correct.
- iOS Safari → Share → Add to Home Screen: correct icon and name, the
  `black-translucent` status bar, no white flash on launch (background color).
- `curl -I https://tedh.gg/manifest.webmanifest` returns 200 with
  `content-type: application/manifest+json`.

## Manual — layout (per release touching a data-heavy page)

- Real device or DevTools device mode at 390×844: no horizontal scroll on
  `/`, `/tournaments`, a tournament detail (bracket tab), `/commanders`, a
  commander detail, `/regional-elo`, a player profile, `/tournament-likelihood`,
  `/trap-spice`.
- The pod bracket (`/tournaments/[slug]` → Bracket) stacks vertically on a
  phone; all stage headings are reachable without horizontal scroll.
- Notched device in landscape: content clears the notch (safe-area insets).

## Performance (optional, before/after motif or hero changes)

- Lighthouse mobile (`npx lighthouse https://tedh.gg --form-factor=mobile`,
  or PageSpeed Insights). Watch paint metrics around the MotifLayer changes —
  the large decorative blobs are hidden below `md:` and
  `background-attachment` drops to `scroll` on phones.
