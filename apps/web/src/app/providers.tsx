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
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN as string, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      defaults: '2026-01-30',
      capture_pageview: false, // turned off to avoid double-counting
      capture_performance: true,
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
