'use client'

import { usePathname, useSearchParams } from "next/navigation"
import { useEffect } from "react"
import posthog from 'posthog-js'
import { PostHogProvider as PHProvider } from '@posthog/react'

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN as string, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      defaults: '2026-01-30',
      capture_pageview: true,
      capture_performance: true,
    })
  }, [])

  // Track pageviews on navigation
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

  return (
    <PHProvider client={posthog}>
      {children}
    </PHProvider>
  )
}
