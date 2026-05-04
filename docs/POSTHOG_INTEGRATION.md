/**
 * PostHog Analytics Integration Guide for tedh.gg
 * 
 * This file demonstrates how to integrate PostHog analytics tracking throughout
 * the application. PostHog provides:
 * 
 * - Session Replays: Watch how users interact with pages
 * - Page Leave: Track bounce rates and session durations accurately
 * - Event Tracking: Capture custom events like commander searches
 * - Performance Metrics: LCP, FID, CLS, TTFB out of the box
 * - Feature Flags: Gradual rollouts and A/B testing
 * 
 * =============================================================================
 * BASIC USAGE
 * =============================================================================
 * 
 * Import the analytics utilities from the lib:
 * 
 *   import { trackCommanderView } from '@/lib/analytics'
 * 
 * Then call them in your components:
 * 
 *   trackCommanderView(commanderId, commanderName)
 * 
 * =============================================================================
 * AVAILABLE TRACKING FUNCTIONS
 * =============================================================================
 * 
 * Page Views:
 *   trackPageView(path)                    - Track generic page views
 * 
 * Commander Features:
 *   trackCommanderView(id, name)          - User viewed a commander page
 *   trackCommanderSearch(query, count)     - User searched commanders
 *   trackCommanderTrendView(id, range)     - User viewed commander trends
 * 
 * Regional Elo:
 *   trackRegionalEloView(region)          - User viewed regional leaderboard
 *   trackPlayerProfileView(id, region)     - User viewed a player profile
 *   trackVsMatchupView(p1, p2)            - User viewed VS comparison
 *   trackRegionChange(from, to)            - User changed region selection
 * 
 * Tournaments:
 *   trackTournamentLikelihoodView()        - User viewed tournament likelihood
 *   trackTournamentAnalysis(tid, cid)      - User generated tournament analysis
 * 
 * Engagement:
 *   trackSessionDuration(seconds)          - User session duration
 *   trackRageClick(element, count)         - User rage-clicked (repeated clicks)
 * 
 * Errors:
 *   trackError(type, message, context)      - Capture application errors
 * 
 * Performance:
 *   trackApiLatency(endpoint, ms, ok)     - Track API response times
 * 
 * =============================================================================
 * EXAMPLE: Adding to a Commander Detail Page
 * =============================================================================
 * 
 * // apps/web/src/app/commanders/[id]/page.tsx
 * 
 * 'use client'
 * 
 * import { useEffect } from 'react'
 * import { trackCommanderView, trackPageView } from '@/lib/analytics'
 * 
 * export default function CommanderPage({ params }: { params: { id: string } }) {
 *   useEffect(() => {
 *     trackPageView(`/commanders/${params.id}`)
 *     trackCommanderView(params.id, commanderName)
 *   }, [params.id])
 * 
 *   // ... rest of component
 * }
 * 
 * =============================================================================
 * EXAMPLE: Tracking Search
 * =============================================================================
 * 
 * import { trackCommanderSearch } from '@/lib/analytics'
 * 
 * function handleSearch(query: string, results: Commander[]) {
 *   trackCommanderSearch(query, results.length)
 * }
 * 
 * =============================================================================
 * EXAMPLE: Identifying Users (Authenticated)
 * =============================================================================
 * 
 * import { identifyUser } from '@/lib/analytics'
 * 
 * // When user logs in
 * identifyUser(user.email, {
 *   email: user.email,
 *   name: user.name,
 *   created_at: user.createdAt,
 * })
 * 
 * // When user logs out
 * import { resetUser } from '@/lib/analytics'
 * resetUser()
 * 
 * =============================================================================
 * EXAMPLE: Capturing Performance Manually
 * =============================================================================
 * 
 * import { trackApiLatency } from '@/lib/analytics'
 * 
 * async function fetchCommanders() {
 *   const start = Date.now()
 *   try {
 *     const data = await api.get('/commanders')
 *     trackApiLatency('/commanders', Date.now() - start, true)
 *     return data
 *   } catch (e) {
 *     trackApiLatency('/commanders', Date.now() - start, false)
 *     throw e
 *   }
 * }
 * 
 * =============================================================================
 * POSTHOG DASHBOARD SETUP
 * =============================================================================
 * 
 * After deploying, set up these dashboards in PostHog:
 * 
 * 1. User Activity Dashboard
 *    - Monthly Active Users
 *    - Session counts by page
 *    - Top commanders viewed
 *    - Search query frequency
 * 
 * 2. Performance Dashboard  
 *    - Average LCP (target: < 2.5s)
 *    - Average TTFB (target: < 800ms)
 *    - Error rates by page
 * 
 * 3. Engagement Dashboard
 *    - Session duration histogram
 *    - Pages per session
 *    - Return visit rate
 * 
 * 4. Regional Elo Dashboard
 *    - Regional usage breakdown
 *    - Player profile views
 *    - VS matchup queries
 * 
 * =============================================================================
 * REVERSE PROXY CONFIGURATION
 * =============================================================================
 * 
 * To improve tracking reliability and bypass ad-blockers, we use a managed 
 * reverse proxy at: https://metrics.tedh.gg
 * 
 * This is configured in `apps/web/src/app/providers.tsx` via the `api_host` 
 * and `ui_host` options.
 * 
 * Environment Variables:
 *   NEXT_PUBLIC_POSTHOG_HOST=https://metrics.tedh.gg
 *   NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN=your_ph_project_token_here
 * 
 * =============================================================================
 * DEBUGGING
 * =============================================================================
 * 
 * In development, set NEXT_PUBLIC_POSTHOG_DEBUG=true to see events in console.
 * 
 * You can also visit https://app.posthog.com/debugger to see live events.
 * 
 * =============================================================================
 * PRIVACY CONSIDERATIONS
 * =============================================================================
 * 
 * PostHog is privacy-first:
 * - No cookies by default (uses localStorage)
 * - GDPR compliant with data anonymization
 * - Users can opt-out via browser extension
 * - Session recordings exclude sensitive fields
 * 
 * Consider adding a privacy policy link if required for your jurisdiction.
 */

export {}
