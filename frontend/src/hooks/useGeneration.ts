import { useState, useCallback } from 'react'
import { apiClient } from '@/services/api'

export interface GenerationProgress {
  status: string
  progress: number
  current_step: string
  estimated_time_remaining: number
  error?: string
}

export interface JobStatus {
  id: string
  status: string
  progress: number
  result?: Record<string, any>
  error?: string
}

export const useGeneration = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Trigger generation for campaign (legacy)
  const generateVideo = useCallback(async (campaignId: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post(
        `/api/generation/campaigns/${campaignId}/generate/`
      )
      return response.data
    } catch (err: any) {
      // 409 Conflict means generation already started - treat as success
      if (err?.response?.status === 409) {
        console.log('✅ Generation already in progress (409)')
        return { message: 'Generation already in progress' }
      }
      
      const message = err instanceof Error ? err.message : 'Failed to generate video'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Trigger generation for campaign
  const generateCampaign = useCallback(async (campaignId: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post(
        `/api/generation/campaigns/${campaignId}/generate`
      )
      return response.data
    } catch (err: any) {
      // 409 Conflict means generation already started - treat as success
      if (err?.response?.status === 409) {
        console.log('✅ Generation already in progress (409)')
        return { message: 'Generation already in progress' }
      }
      
      const message = err instanceof Error ? err.message : 'Failed to generate video'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Get generation progress for campaign (legacy)
  const getProgress = useCallback(async (campaignId: string, signal?: AbortSignal) => {
    // Validate campaignId - guard against undefined/null/string "undefined"
    if (!campaignId || campaignId === 'undefined' || campaignId === 'null') {
      const error = new Error('Invalid campaign ID')
      setError('Invalid campaign ID')
      throw error
    }

    try {
      const response = await apiClient.get(
        `/api/generation/campaigns/${campaignId}/progress`, // Removed trailing slash to prevent redirect loop
        { signal, timeout: 10000 } // 10 second timeout
      )
      return response.data as GenerationProgress
    } catch (err: any) {
      // Don't throw error if request was aborted (normal cleanup behavior)
      if (err?.name === 'AbortError' || err?.code === 'ERR_CANCELED' || err?.message === 'canceled') {
        // Silent abort - this is normal when component unmounts or re-renders
        throw { silent: true, message: 'canceled' }
      }
      const message = err instanceof Error ? err.message : 'Failed to fetch progress'
      setError(message)
      throw err
    }
  }, [])

  // Get generation progress for campaign
  const getCampaignProgress = useCallback(async (campaignId: string, signal?: AbortSignal) => {
    // Validate campaignId - guard against undefined/null/string "undefined"
    if (!campaignId || campaignId === 'undefined' || campaignId === 'null') {
      const error = new Error('Invalid campaign ID')
      setError('Invalid campaign ID')
      throw error
    }

    try {
      const response = await apiClient.get(
        `/api/generation/campaigns/${campaignId}/progress`,
        { signal, timeout: 10000 } // 10 second timeout
      )
      return response.data as GenerationProgress
    } catch (err: any) {
      // Don't throw error if request was aborted (normal cleanup behavior)
      if (err?.name === 'AbortError' || err?.code === 'ERR_CANCELED' || err?.message === 'canceled') {
        // Silent abort - this is normal when component unmounts or re-renders
        throw { silent: true, message: 'canceled' }
      }
      const message = err instanceof Error ? err.message : 'Failed to fetch progress'
      setError(message)
      throw err
    }
  }, [])

  // Get job status
  const getJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await apiClient.get(`/api/generation/jobs/${jobId}/status/`)
      return response.data as JobStatus
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch job status'
      setError(message)
      throw err
    }
  }, [])

  // Cancel generation
  const cancelGeneration = useCallback(async (campaignId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.post(`/api/generation/campaigns/${campaignId}/cancel/`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to cancel generation'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Reset campaign
  const resetCampaign = useCallback(async (campaignId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.post(`/api/generation/campaigns/${campaignId}/reset/`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reset campaign'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Select variation (Phase 4: Multi-variation feature)
  const selectVariation = useCallback(async (campaignId: string, variationIndex: number) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post(
        `/api/generation/campaigns/${campaignId}/select-variation`,
        { variation_index: variationIndex }
      )
      return response.data
    } catch (err: any) {
      const message = err?.response?.data?.detail || err instanceof Error ? err.message : 'Failed to select variation'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    loading,
    error,
    generateVideo,
    generateCampaign,
    getProgress,
    getCampaignProgress,
    getJobStatus,
    cancelGeneration,
    resetCampaign,
    selectVariation,
  }
}

