'use client'

import React from 'react'
import { usePostHog } from '@posthog/react'
import { useEffect } from 'react'

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class AnalyticsErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Capture exception to PostHog
    if (typeof window !== 'undefined') {
      const posthog = (window as unknown as { posthog?: typeof import('posthog-js').default }).posthog
      if (posthog) {
        posthog.captureException(error, {
          component_stack: errorInfo.componentStack,
          ...errorInfo,
        })
      }
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-foreground">Something went wrong</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              We&apos;ve logged this error and are working to fix it.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Hook for capturing React errors
export function useErrorCapture() {
  const posthog = usePostHog()

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      posthog.captureException(event.error || new Error(event.message), {
        type: 'unhandled_error',
      })
    }

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      posthog.captureException(event.reason, {
        type: 'unhandled_rejection',
      })
    }

    window.addEventListener('error', handleError)
    window.addEventListener('unhandledrejection', handleUnhandledRejection)

    return () => {
      window.removeEventListener('error', handleError)
      window.removeEventListener('unhandledrejection', handleUnhandledRejection)
    }
  }, [posthog])
}
