/**
 * PostHog Analytics Utilities
 * 
 * Provides typed wrappers for custom analytics events in the tedh.gg application.
 * This centralizes analytics tracking to ensure consistency and makes it easy to
 * add new events as we learn more about user behavior.
 */

import posthog from 'posthog-js'

// =============================================================================
// Page/Section Events
// =============================================================================

export const trackPageView = (path: string, properties?: Record<string, unknown>) => {
  posthog.capture('$pageview', {
    path,
    ...properties,
  })
}

// =============================================================================
// Commander Events
// =============================================================================

export const trackCommanderView = (commanderId: string, commanderName: string) => {
  posthog.capture('commander_viewed', {
    commander_id: commanderId,
    commander_name: commanderName,
  })
}

export const trackCommanderSearch = (query: string, resultCount: number) => {
  posthog.capture('commander_searched', {
    query,
    result_count: resultCount,
  })
}

export const trackCommanderTrendView = (commanderId: string, timeRange: string) => {
  posthog.capture('commander_trends_viewed', {
    commander_id: commanderId,
    time_range: timeRange,
  })
}

// =============================================================================
// Regional Elo Events
// =============================================================================

export const trackRegionalEloView = (region: string) => {
  posthog.capture('regional_elo_viewed', {
    region,
  })
}

export const trackPlayerProfileView = (topdeckId: string, region: string) => {
  posthog.capture('player_profile_viewed', {
    topdeck_id: topdeckId,
    region,
  })
}

export const trackVsMatchupView = (playerTopdeckId: string, opponentTopdeckId: string) => {
  posthog.capture('vs_matchup_viewed', {
    player_topdeck_id: playerTopdeckId,
    opponent_topdeck_id: opponentTopdeckId,
  })
}

export const trackRegionChange = (fromRegion: string, toRegion: string) => {
  posthog.capture('region_changed', {
    from_region: fromRegion,
    to_region: toRegion,
  })
}

// =============================================================================
// Tournament Events
// =============================================================================

export const trackTournamentLikelihoodView = () => {
  posthog.capture('tournament_likelihood_viewed')
}

export const trackTournamentAnalysis = (tournamentId: string, commanderId: string) => {
  posthog.capture('tournament_analysis_generated', {
    tournament_id: tournamentId,
    commander_id: commanderId,
  })
}

// =============================================================================
// User Engagement Events
// =============================================================================

export const trackSessionDuration = (durationSeconds: number) => {
  posthog.capture('session_duration', {
    duration_seconds: durationSeconds,
  })
}

export const trackRageClick = (element: string, clickCount: number) => {
  posthog.capture('$rageclick', {
    element,
    click_count: clickCount,
  })
}

// =============================================================================
// Error Events
// =============================================================================

export const trackError = (errorType: string, errorMessage: string, context?: Record<string, unknown>) => {
  posthog.captureException(new Error(errorMessage), {
    error_type: errorType,
    ...context,
  })
}

// =============================================================================
// Feature Adoption Events
// =============================================================================

export const trackNewFeatureInteracted = (featureName: string, action: 'clicked' | 'viewed' | 'used') => {
  posthog.capture('feature_interaction', {
    feature_name: featureName,
    action,
  })
}

// =============================================================================
// Performance Events
// =============================================================================

export const trackApiLatency = (endpoint: string, latencyMs: number, success: boolean) => {
  posthog.capture('api_latency', {
    endpoint,
    latency_ms: latencyMs,
    success,
  })
}

// =============================================================================
// User Identification
// =============================================================================

export const identifyUser = (distinctId: string, properties?: Record<string, unknown>) => {
  posthog.identify(distinctId, properties)
}

export const resetUser = () => {
  posthog.reset()
}
