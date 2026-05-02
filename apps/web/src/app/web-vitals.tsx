'use client'

import { useReportWebVitals } from 'next/web-vitals'
import { usePostHog } from '@posthog/react'

interface VitalMetric {
  name: string
  value: number
  id: string
  delta: number
  rating: 'good' | 'needs-improvement' | 'poor'
  entries: PerformanceEntry[]
}

export function WebVitals() {
  const posthog = usePostHog()

  useReportWebVitals((metric: VitalMetric) => {
    // Capture core web vitals
    posthog.capture(metric.name, {
      value: metric.value,
      delta: metric.delta,
      id: metric.id,
      rating: metric.rating,
      // Core metrics
      ...(metric.name === 'LCP' && { metric_type: 'largest_contentful_paint' }),
      ...(metric.name === 'FID' && { metric_type: 'first_input_delay' }),
      ...(metric.name === 'CLS' && { metric_type: 'cumulative_layout_shift' }),
      ...(metric.name === 'TTFB' && { metric_type: 'time_to_first_byte' }),
      ...(metric.name === 'INP' && { metric_type: 'interaction_to_next_paint' }),
      ...(metric.name === 'FCP' && { metric_type: 'first_contentful_paint' }),
    })
  })

  return null
}
