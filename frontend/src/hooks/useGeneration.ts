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

  // Trigger generation
  const generateVideo = useCallback(async (projectId: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post(
        `/api/generation/projects/${projectId}/generate/`
      )
      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate video'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Get generation progress
  const getProgress = useCallback(async (projectId: string, signal?: AbortSignal) => {
    try {
      const response = await apiClient.get(
        `/api/generation/projects/${projectId}/progress`, // Removed trailing slash to prevent redirect loop
        { signal, timeout: 10000 } // 10 second timeout
      )
      return response.data as GenerationProgress
    } catch (err: any) {
      // Don't throw error if request was aborted
      if (err?.name === 'AbortError' || err?.code === 'ERR_CANCELED') {
        throw err
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
  const cancelGeneration = useCallback(async (projectId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.post(`/api/generation/projects/${projectId}/cancel/`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to cancel generation'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Reset project
  const resetProject = useCallback(async (projectId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.post(`/api/generation/projects/${projectId}/reset/`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reset project'
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
    getProgress,
    getJobStatus,
    cancelGeneration,
    resetProject,
  }
}

