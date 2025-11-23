import { useState, useEffect, useCallback, useRef } from 'react'
import { useGeneration, type GenerationProgress } from './useGeneration'

interface UseProgressPollingOptions {
  campaignId?: string
  campaignId?: string
  enabled?: boolean
  interval?: number
  onComplete?: () => void
  onError?: (error: string) => void
}

export const useProgressPolling = ({
  campaignId,
  campaignId,
  enabled = true,
  interval = 2000,
  onComplete,
  onError,
}: UseProgressPollingOptions) => {
  const { getProgress, getCampaignProgress } = useGeneration()
  const id = campaignId || campaignId || ''
  const isCampaign = !!campaignId
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [loading, setLoading] = useState(false)
  const [isPolling, setIsPolling] = useState(false)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const consecutiveErrorsRef = useRef(0)
  const maxConsecutiveErrors = 5
  
  // Use refs for callbacks to prevent re-creation
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)
  
  // Update refs when callbacks change
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  }, [onComplete, onError])

  const poll = useCallback(async () => {
    if (!enabled || !id) return

    // Cancel any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController()

    try {
      setLoading(true)
      const data = isCampaign
        ? await getCampaignProgress(id, abortControllerRef.current.signal)
        : await getProgress(id, abortControllerRef.current.signal)
      
      // Reset error counter on success
      consecutiveErrorsRef.current = 0
      
      setProgress(data)

      // Check if generation is complete
      if (
        data.status === 'COMPLETED' ||
        data.status === 'completed'
      ) {
        setIsPolling(false)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        onCompleteRef.current?.()
        return
      }

      // Check for errors
      if (data.status === 'FAILED' || data.status === 'failed') {
        setIsPolling(false)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        onErrorRef.current?.(data.error || 'Generation failed')
        return
      }
    } catch (err: any) {
      // Don't handle aborted requests as errors
      if (err?.name === 'AbortError' || err?.message?.includes('aborted')) {
        return
      }

      consecutiveErrorsRef.current += 1
      const message = err instanceof Error ? err.message : 'Failed to fetch progress'
      
      // Stop polling after too many consecutive errors
      if (consecutiveErrorsRef.current >= maxConsecutiveErrors) {
        setIsPolling(false)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        onErrorRef.current?.(`Too many errors. Last error: ${message}`)
        return
      }

      // Check if this is a silent error (like abort/canceled) - don't report these
      const isSilentError = (err as any)?.silent === true || message === 'canceled'
      
      if (!isSilentError) {
        // Log error but continue polling (might be temporary network issue)
        console.warn(`Polling error (${consecutiveErrorsRef.current}/${maxConsecutiveErrors}):`, message)
        onErrorRef.current?.(message)
      }
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }, [id, enabled, isCampaign, getProgress, getCampaignProgress])

  // Start polling on mount or when id changes
  useEffect(() => {
    if (!enabled || !id) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      setIsPolling(false)
      return
    }

    setIsPolling(true)
    consecutiveErrorsRef.current = 0

    // Poll immediately
    poll()

    // Then set up interval
    const intervalId = setInterval(() => {
      poll()
    }, interval)
    pollIntervalRef.current = intervalId

    return () => {
      // Cleanup: clear interval
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      // Cleanup: abort any pending request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
      setIsPolling(false)
    }
  }, [id, enabled, interval, poll]) // Added poll to dependencies

  // Manual stop polling
  const stopPolling = useCallback(() => {
    setIsPolling(false)
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
  }, [])

  // Manual start polling
  const startPolling = useCallback(() => {
    setIsPolling(true)
    poll()
    pollIntervalRef.current = setInterval(poll, interval)
  }, [poll, interval])

  // Manual refresh
  const refresh = useCallback(async () => {
    await poll()
  }, [poll])

  return {
    progress,
    loading,
    isPolling,
    stopPolling,
    startPolling,
    refresh,
  }
}

