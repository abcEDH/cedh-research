# 0011 - PostHog for Product Analytics and Error Capture

## Status
Accepted

## Context
The product had no instrumentation, which made it impossible to answer:
- Which pages users actually visit.
- Which client-side errors users encounter.
- What the Largest Contentful Paint distribution looks like in the wild.
- Which features are sticky vs. ignored.

Decision criteria: a single tool that covers product analytics, session replay, error capture, and Web Vitals; that ships a typed React SDK; that is willing to host data in the US for compliance simplicity; and whose pricing is workable for a small project at this scale.

## Decision
Adopt PostHog (US Cloud, project ID `371705`) as the single product-analytics + error-capture surface for `apps/web/`.

**Wiring**
- Client init in `apps/web/src/app/providers.tsx` via `posthog.init(token, { defaults: '2026-01-30', ... })`.
- Pageviews captured manually in `PostHogPageviewTracker` (built-in `capture_pageview` is disabled to avoid double-counting under App Router).
- Web Vitals piped via `apps/web/src/app/web-vitals.tsx`.
- React errors caught by `AnalyticsErrorBoundary` and shipped via `posthog.captureException`.
- Typed event helpers live in `apps/web/src/lib/analytics.ts`.

**Configuration**
- Token (`NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN`) stored in 1Password ("PostHog - cedh-research"), Vercel (sensitive on prod/preview, non-sensitive on development), and GitHub Secrets.
- `NEXT_PUBLIC_POSTHOG_DEBUG=true` in local dev exposes `window.posthog` and logs `distinct_id` for verification.
- `NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com`.

## Consequences

**Easier**
- Single dashboard for usage, errors, replays, and Web Vitals.
- Bot detection (`navigator.webdriver`) is on by default — automation traffic does not pollute event volume.
- Self-hosting is an exit option later if pricing changes.

**Harder**
- A third-party JS bundle is now in the critical path; if PostHog has an outage, the SDK should not block render.
- The token is embedded in client JS (it's the public ingestion key by design); abuse mitigation lives in PostHog's project-side settings.
- Bot-flagging blocks event capture from headless browsers — local Playwright/E2E verification needs `opt_out_useragent_filter: true` if it must assert ingestion.

### Cross-Repo Impact
`apps/web/` only.

## Sources
- PR #156 — "feat: [Analytics] PostHog integration for user analytics"
- `apps/web/src/app/providers.tsx`
- `apps/web/src/components/analytics/error-boundary.tsx`
- `apps/web/src/app/web-vitals.tsx`
- `apps/web/src/lib/analytics.ts`
