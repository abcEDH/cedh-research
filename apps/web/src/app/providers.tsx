'use client'

import { usePathname, useSearchParams } from "next/navigation"
import { Suspense, useEffect } from "react"
import posthog from 'posthog-js'
import { PostHogProvider as PHProvider } from '@posthog/react'

function PostHogPageviewTracker() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (pathname) {
      const url = searchParams.toString()
        ? `${pathname}?${searchParams.toString()}`
        : pathname
      posthog.capture('$pageview', {
        $current_url: window.location.origin + url,
        path: pathname,
      })
    }
  }, [pathname, searchParams])

  return null
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN
    if (!token) {
      console.warn('[PostHog] NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN is not set — analytics disabled')
      return
    }
    const debug = process.env.NEXT_PUBLIC_POSTHOG_DEBUG === 'true'
    posthog.init(token, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      defaults: '2026-01-30',
      capture_pageview: false, // turned off to avoid double-counting
      capture_performance: true,
      debug,
      loaded: (ph) => {
        if (debug) {
          console.info('[PostHog] loaded — distinct_id:', ph.get_distinct_id())
          ;(window as unknown as { posthog: typeof ph }).posthog = ph
        }
      },
    })
  }, [])

  return (
    <PHProvider client={posthog}>
      <Suspense>
        <PostHogPageviewTracker />
      </Suspense>
      {children}
    </PHProvider>
  )
}
