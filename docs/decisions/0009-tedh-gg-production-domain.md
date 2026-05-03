# 0009 - Production Domain is `tedh.gg`

## Status
Accepted

## Context
The product launched under the working name "cEDH Analytics" / "cEDH Research" and was reachable at `cedh-research.vercel.app`. The chosen public-facing brand is "tedh.gg". After the DNS cutover (Porkbun → Vercel), the codebase still:
- Treated `cedh-research.vercel.app` as the canonical production hostname in CI, sitemap, and metadata.
- Displayed "cEDH Analytics" branding on user-facing surfaces.
- Referenced the old domain in test base URLs and runbooks.

## Decision
- Production hostname is `tedh.gg`. Vercel project alias points there.
- Branding on every public surface is "tedh.gg" / "TEDH Elo".
- E2E test default base URL is `https://tedh.gg` (overridable via `BASE_URL`).
- Cutover and canonical references documented in `docs/production-domain-cutover.md`.

## Consequences

**Easier**
- One canonical URL for marketing, sharing, and SEO.
- E2E and smoke tests run against the real production hostname by default.

**Harder**
- Old links to `cedh-research.vercel.app` must continue to redirect for the foreseeable future.
- DNS / certificate ownership is on Porkbun (registrar) + Vercel (host) — two vendors to coordinate during incidents.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- `docs/production-domain-cutover.md`
- PR #121 — "docs: codify tedh.gg production domain"
- PR #123 — "docs: align public site branding with tedh.gg"
- `apps/web/package.json` `test:e2e:prod` script
