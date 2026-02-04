# Release Lessons - 2026-02-04

## What broke
- Vercel/GitHub preview built from repo root and couldn't find the Next.js `app/` directory.
- Frontend CI failed before checkout because a step used `working-directory: apps/web` too early.
- E2E failures came from strict locator collisions after adding new nav/cards with the same href/text.
- `/regional-elo` returned 404 on one preview because that route lived on a different branch at deploy time.
- `/midseason-invitational` threw a server error when TopDeck leaderboard parsing failed.

## Fixes applied
- Added `vercel.json` at repo root to force web app build commands under `apps/web`.
- Updated `.github/workflows/frontend.yml` so the secrets check runs from repo root.
- Set required GitHub Action secrets:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Updated Playwright tests to avoid strict-mode collisions and target stable page regions.
- Cherry-picked Regional Elo route into the same branch as tournament prep before redeploy.
- Hardened TopDeck ingestion/parsing path and added graceful error UI on MidSeason page.

## Release checklist for next minor
- Confirm preview contains all new routes:
  - `/tournament-likelihood`
  - `/midseason-invitational`
  - `/regional-elo`
- Re-run Frontend CI and verify all Playwright tests pass.
- Verify Vercel status check on PR head commit is green.
- Spot-check TopDeck-powered pages with and without upstream data available.

## Process improvements
- Prefer one feature branch for user-visible linked pages that should ship together.
- When adding nav/feature links, update E2E selectors in the same commit.
- Add a release sanity script later to smoke-test critical routes before merge.
