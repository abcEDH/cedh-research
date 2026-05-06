# 0002 - Next.js App Router + React 19 + Tailwind v4 Web Stack

## Status
Accepted

## Context
The web surface (tedh.gg) is a read-heavy dashboard for cEDH players: commander rankings, tournament data, regional Elo leaderboards, player profiles. It needs:
- Server-side data fetching from Supabase with route-scoped caching
- Strong static-rendering story for SEO and Core Web Vitals
- Charting (Recharts) and rich interactive controls (Radix primitives)
- A modern styling system that does not require a separate build step

## Decision
- **Framework:** Next.js (App Router) — currently `^16.1.6`. Server Components are the default; client components are opt-in via `'use client'`.
- **React:** `19.2.3`.
- **Styling:** Tailwind CSS v4 (via `@tailwindcss/postcss`) with no separate `tailwind.config.js` — config lives in CSS.
- **Component primitives:** Radix UI (`@radix-ui/react-select`, `tabs`, `tooltip`, `slot`, `slider`) wrapped with `class-variance-authority` and `tailwind-merge` (shadcn-style).
- **Data:** `@supabase/supabase-js` for queries; server-only paths use `server-only` to enforce boundary.
- **Charts:** Recharts.
- **Icons:** lucide-react.

## Consequences

**Easier**
- Server Components let leaderboard pages render without shipping the data layer to the client.
- App Router's `unstable_cache` and route-segment caching map cleanly to read-heavy pages (see ADR 0006).
- Tailwind v4's CSS-first config eliminates one config file.

**Harder**
- React 19 + Next 16 are recent — some libraries (PostHog React) need vetting against the version.
- App Router's mental model is non-trivial; `useSearchParams` requires Suspense (PR #59 fix).
- Class-component error boundaries still required (no functional equivalent yet) — see `apps/web/src/components/analytics/error-boundary.tsx`.

### Cross-Repo Impact
`apps/web/` only.

## Sources
- `apps/web/package.json` dependencies
- `apps/web/README.md` "Tech stack"
- PR #59 (`fix(web): wrap useSearchParams in Suspense to fix build`)
