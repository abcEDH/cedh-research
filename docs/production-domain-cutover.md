# Production Domain Cutover

This runbook records the `tedh.gg` production-domain migration for the Vercel-hosted web app.

## Final state
- Registrar and DNS host: Porkbun
- App host: Vercel project `cedh-research`
- Canonical production domains: `tedh.gg` and `www.tedh.gg`
- Current production deployment alias: `web-theta-blush-49.vercel.app`
- Fallback Vercel alias still present: `cedh-research.vercel.app`

## 2026-04-28 observed outcome
- `tedh.gg`, `www.tedh.gg`, and `web-theta-blush-49.vercel.app` all resolved to deployment `dpl_5fcKFeYE7KJVwnn3zEPeabFfTEvT` created on April 28, 2026.
- `cedh-research.vercel.app` remained on older deployment `dpl_EraFaWwa9Pw1LENY1FLzRVJU94kw` created on April 21, 2026.
- Production E2E passed against both `web-theta-blush-49.vercel.app` and `cedh-research.vercel.app` during the migration window.
- Conclusion: `tedh.gg` is the canonical production hostname. `cedh-research.vercel.app` remains as a fallback alias.

## What we changed
1. Added `tedh.gg` to the `cedh-research` Vercel project:
   - `vercel domains add tedh.gg`
2. Added `www.tedh.gg` to the same Vercel project:
   - `vercel domains add www.tedh.gg`
3. Replaced Porkbun parking with Vercel DNS targets:
   - `A @ -> 76.76.21.21`
   - `CNAME www -> cname.vercel-dns.com`
4. Pointed the production alias to the intended production deployment:
   - `TARGET_ALIAS=tedh.gg ./scripts/manual-vercel-alias.sh web-theta-blush-49.vercel.app`

## DNS lessons
- Buying a domain and adding it in Vercel is not enough. Public DNS delegation must propagate before Vercel can verify the hostname.
- For this fresh `.gg` registration, Porkbun authoritative nameservers served the correct `A` record before public resolvers like `8.8.8.8` and `1.1.1.1` did.
- During propagation, these checks were useful:
  - `dig +short tedh.gg @curitiba.ns.porkbun.com`
  - `dig +short tedh.gg @8.8.8.8`
  - `dig +short tedh.gg @1.1.1.1`
  - `vercel domains inspect tedh.gg`

## Verification commands
- `vercel inspect tedh.gg`
- `vercel inspect web-theta-blush-49.vercel.app`
- `vercel inspect cedh-research.vercel.app`
- `open https://tedh.gg`
- `open https://www.tedh.gg`
- `BASE_URL=https://web-theta-blush-49.vercel.app npm --workspace apps/web run test:e2e`

`tedh.gg` and `web-theta-blush-49.vercel.app` should resolve to the same deployment id after cutover.

## What should be codified
- GitHub Actions production environment URL should use `https://tedh.gg`.
- Production alias automation should default `TARGET_ALIAS` to `tedh.gg`.
- Prod E2E should default to `https://tedh.gg`.
- Release QA should explicitly verify that `tedh.gg` and `web-theta-blush-49.vercel.app` resolve to the same deployment.
- A repository variable `PRODUCTION_DOMAIN=tedh.gg` should be set so the hostname is explicit outside workflow defaults.
- `cedh-research.vercel.app` should remain available as a fallback alias and be checked during release verification.

## Repo follow-up in this branch
- `.github/workflows/cd.yml` defaults production aliasing to `tedh.gg`
- `scripts/manual-vercel-alias.sh` defaults `TARGET_ALIAS` to `tedh.gg`
- `apps/web/package.json` defaults prod E2E to `https://tedh.gg`
- `apps/web/CONTEXT.md` lists `https://tedh.gg` as the live site
- `docs/qa-release-checklist.md` references `tedh.gg` as the production domain
