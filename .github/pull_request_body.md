## Problem
We need visibility into how users interact with tedh.gg to improve the product. Without analytics, we can't answer questions like: what pages do users visit most, what bugs are they encountering, what are the LCPs, how long are sessions, and who is actually using the product.

## Decision
Integrate PostHog as the analytics platform for post-hoc analytics, providing:
- Session recordings to understand user behavior
- Core Web Vitals (LCP, FID, CLS, TTFB) for performance monitoring  
- Custom event tracking for domain-specific interactions
- Error tracking to identify bugs users encounter

## Scope
- Add PostHog client-side integration via `posthog-js` and `@posthog/react`
- Add typed analytics utilities in `lib/analytics.ts` for commander, regional Elo, and tournament features
- Add Web Vitals capture for performance monitoring
- Add error boundary component for React error capture
- Add environment variable configuration template
- Add integration documentation

## Non-goals
- This PR does not instrument backend services
- This PR does not include user authentication/identification (requires TopDeck auth integration)
- This PR does not configure feature flags

## Reviewer Guide
1. Start with `apps/web/src/app/providers.tsx` for the PostHog provider setup
2. Review `apps/web/src/lib/analytics.ts` for the typed tracking functions
3. Check `docs/POSTHOG_INTEGRATION.md` for usage examples
4. Verify `.env.example` has the correct environment variable names
5. Ensure the root layout properly wraps children in PostHogProvider

## QA Instructions
1. Copy `.env.example` to `.env.local` and add your PostHog project token
2. Run `npm run dev` and visit http://localhost:3000
3. Open browser DevTools > Network and confirm PostHog requests are made
4. Visit https://app.posthog.com/debugger to see live events
5. Navigate between pages and verify `$pageview` events appear
6. For Web Vitals, check for `LCP`, `FCP`, `CLS` events in the debugger

## Testing
- [x] `npm run lint` passes with no errors
- [x] TypeScript compilation check passes (`npx tsc --noEmit`)
- [ ] E2E test with actual PostHog token (requires token from 1Password)
- [ ] Screenshot of PostHog debugger showing pageview events

## Risks
- User-facing risk: Low - analytics are opt-out by default, no PII collected without auth
- Data or migration risk: None - no database changes
- CI or deploy risk: Low - only adds new dependencies, existing tests unaffected

## Codex Review
- After CI starts, comment `@codex review` on this PR for an automated pass.
- Treat Codex feedback as advisory. Human reviewers still own the final merge decision.
