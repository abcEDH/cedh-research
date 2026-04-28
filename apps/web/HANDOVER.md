# Handover Notes

## Data cleanup

- The frontend now filters out rows where `commander_name` is "Unknown Commander" for both the main table and the top win rate list.
- If "Unknown Commander" appears, it should be cleaned at the data layer (Supabase) or excluded in the API query.

## 2026-01-26 — Trend queries (potentially heavy)
- The new WoW/MoM trend tables on `/commanders` and `/commanders/trends` currently derive weekly/monthly aggregates by scanning `tournament_entries` joined to `tournaments` (start_date).
- This can become expensive as data grows. Suggested materialized views:

### Suggested view: commander_weekly_trends
Aggregate per commander per ISO week.

**Fields**: commander_id, week_key, entries, wins, losses, draws, win_rate

### Suggested view: commander_monthly_trends
Aggregate per commander per month.

**Fields**: commander_id, month_key, entries, wins, losses, draws, win_rate

### Suggested derived view: commander_wow_mom
Join latest vs previous week/month to compute WoW/MoM deltas for entries (%) and win rate (pp).

If you add these, we can swap the UI to read directly from the materialized views instead of scanning `tournament_entries`.

## Release/versioning automation
- Semantic Release runs on push to `main` via `.github/workflows/frontend.yml` and also remains available as a manual fallback in `.github/workflows/release.yml`.
- The semantic release step updates `CHANGELOG.md`, bumps `package.json` version, creates a git tag, and publishes a GitHub Release.
- Production aliasing is owned by `.github/workflows/cd.yml`, which resolves the matching Vercel deployment for the current `main` commit and points `tedh.gg` at it.
- The alias target is also configurable through the GitHub repository variable `PRODUCTION_DOMAIN` if production hostname changes again.
- As of April 28, 2026, `tedh.gg`, `www.tedh.gg`, and `web-theta-blush-49.vercel.app` all resolved to the latest production deployment, while `cedh-research.vercel.app` remained on an older deployment and should be treated as a legacy alias until explicitly handled.
- Deploy tags were removed; deploy state is tracked by Vercel deployment metadata and GitHub release history instead.
- Requires GitHub Actions permissions: `contents: write` for release tagging and `VERCEL_TOKEN` for production aliasing.

## 2026-01-26 — Trend views wiring
- Frontend trends now read from `commander_wow_mom` (WoW/MoM deltas) and `commander_weekly_trends` (sparklines).
- If view schemas change, update `src/app/commanders/page.tsx` and `src/app/commanders/trends/page.tsx`.
