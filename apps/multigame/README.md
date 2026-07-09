# apps/multigame

Multi-tenant Next.js app serving tournament meta sites for the non-cEDH games ingested by
this repo's backend: **Riftbound** (`riftbound.tedh.gg`), **Gundam Card Game**
(`gundam.tedh.gg`), and **Yu-Gi-Oh Retro** (`retro.tedh.gg`). One deployment serves every
tenant; per-game branding, formats, and compliance text come from the game registry
(`src/lib/games/registry.ts`).

## Tenancy model

`src/proxy.ts` (Next 16's middleware, formerly `middleware.ts`) rewrites every request to an
internal `/[game]/...` route tree. Resolution order (see `src/lib/games/resolve-tenant.ts`):

1. Path already prefixed with a valid game slug — passes through untouched.
2. `?game=<slug>` query override — for local dev and Vercel previews, e.g.
   `http://localhost:3000/?game=gundam`.
3. First hostname label — `riftbound.tedh.gg` (production) or `riftbound.localhost:3000`
   (local; modern browsers resolve `*.localhost` without `/etc/hosts` edits).
4. `NEXT_PUBLIC_DEFAULT_GAME` env var, falling back to `riftbound`.

The tenant layout (`src/app/(tenant)/[game]/layout.tsx`) wraps each page in
`<div data-game="<slug>">`; per-tenant palettes in `src/app/globals.css` key off that
attribute and override only `--primary` / `--accent` / `--ring` / `--chart-*`.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL. Placeholder fallback keeps `next build` working; pages render an informative empty state. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (read-only access via RLS). |
| `NEXT_PUBLIC_DEFAULT_GAME` | Tenant used when the hostname doesn't match any game slug (optional, defaults to `riftbound`). |

## Local development

```bash
npm ci                      # from the repo root (npm workspaces)
npm run multigame:dev       # then visit http://riftbound.localhost:3000
npm run multigame:test:ci   # vitest
npm run multigame:lint      # eslint
./scripts/verify-multigame.sh  # full CI-equivalent harness
```

## Data attribution and compliance

- Tournament data is provided by [TopDeck.gg](https://topdeck.gg). This project is not
  affiliated with TopDeck.gg; every page footer carries attribution.
- Each tenant footer also renders a per-publisher fan-content notice from
  `GameConfig.compliance` (Riot Games for Riftbound, BANDAI/SOTSU/SUNRISE for Gundam,
  Konami for Yu-Gi-Oh). Keep these notices intact when touching layout code.
- Yu-Gi-Oh card images are served by [YGOPRODeck](https://ygoprodeck.com); Riftbound and
  Gundam currently use no card-image provider.

## Manual operations (one-time setup)

1. **Second Vercel project** pointing at this repo with `rootDirectory: apps/multigame`
   (the existing project serves `apps/web`). Framework: Next.js; `vercel.json` here sets
   the build/install commands and region.
2. **DNS**: CNAME `riftbound.tedh.gg`, `gundam.tedh.gg`, and `retro.tedh.gg` to
   `cname.vercel-dns.com`, then add all three domains to the multigame Vercel project.
3. **Ignored Build Step** per project so pushes only rebuild the app they touch, e.g. for
   this project: `git diff --quiet HEAD^ HEAD -- apps/multigame/ package.json package-lock.json`
   (and the inverse path filter on the `apps/web` project).
4. Set the environment variables above in the Vercel project (placeholders are fine until
   the Supabase read models contain data).

## Known provisional bits

- **Retro `dbFormat` strings are provisional.** The registry pins `"Edison"` / `"Goat"`,
  but these are unverified against live TopDeck data. After the first Yu-Gi-Oh ingestion
  run, confirm with `SELECT DISTINCT format FROM tournaments WHERE game = 'Yu-Gi-Oh'` and
  update `src/lib/games/registry.ts` (see ADR 0015 appendix,
  `docs/decisions/0015-multi-game-single-schema.md`).
