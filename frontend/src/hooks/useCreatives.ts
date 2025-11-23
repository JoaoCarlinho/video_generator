import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'
import type { AspectRatio, SceneBackground } from '@/types'

export interface Creative {
  id: string
  title: string
  brief: string
  brand_name: string
  mood?: string
  duration: number
  status: 'draft' | 'generating' | 'ready' | 'failed' | 'COMPLETED'
  created_at: string
  updated_at: string
  cost_estimate?: number
  output_videos?: Record<string, string>
  progress?: number
  // WAN 2.5: Video provider tracking
  video_provider?: 'replicate' | 'ecs'
  video_provider_metadata?: {
    primary_provider?: string
    actual_provider?: string
    failover_used?: boolean
    failover_reason?: string
    timestamp?: string
    endpoint?: string
    generation_duration_ms?: number
  }
  num_variations?: number // 1-3
  selected_variation_index?: number | null // 0-2 or null
}

interface CreateCreativeInput {
  title: string
  brief?: string
  brand_name: string
  product_name: string
  mood?: string
  duration?: number
  aspect_ratio?: '9:16' | '1:1' | '16:9'
  product_image_url?: string
  productImages?: string[]
  sceneBackgrounds?: SceneBackground[]
  outputFormats?: AspectRatio[]
  output_formats?: string[] // Array of aspect ratios like ['9:16', '16:9']
  logo_url?: string
  guidelines_url?: string
  creative_prompt?: string
  brand_description?: string
  target_audience?: string
  target_duration?: number
  selected_style?: string
  // WAN 2.5: Video provider selection
  video_provider?: 'replicate' | 'ecs'
  // Phase 9: Perfume-specific fields (optional, for backward compatibility)
  perfume_name?: string
  perfume_gender?: 'masculine' | 'feminine' | 'unisex'
  // Phase 3: Multi-variation support
  num_variations?: 1 | 2 | 3 // Number of video variations (1-3)
}

export const useCreatives = () => {
  const { user } = useAuth()
  const [creatives, setCreatives] = useState<Creative[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all creatives for a campaign
  const fetchCreatives = useCallback(async (campaignId: string) => {
    if (!user || !campaignId) return

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get(`/api/campaigns/${campaignId}/creatives`)
      // API returns { creatives: [...], total, limit, offset }
      setCreatives(response.data.creatives || [])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch creatives'
      setError(message)
      console.error('Error fetching creatives:', err)
    } finally {
      setLoading(false)
    }
  }, [user])

  // Create new creative for a campaign
  const createCreative = useCallback(
    async (campaignId: string, input: CreateCreativeInput) => {
      if (!user) throw new Error('Not authenticated')
      if (!campaignId) throw new Error('Campaign ID is required')

      setLoading(true)
      setError(null)

      try {
        // Ensure video_provider defaults to "replicate" if not provided
        const payload = {
          ...input,
          video_provider: input.video_provider || 'replicate',
        }

        const response = await apiClient.post(`/api/campaigns/${campaignId}/creatives`, payload)
        const newCreative = response.data

        setCreatives((prev) => [newCreative, ...prev])

        // Log provider selection for analytics
        console.log('[Creative Created]', {
          creativeId: newCreative.id,
          campaignId,
          provider: newCreative.video_provider || payload.video_provider,
          timestamp: new Date().toISOString(),
        })

        return newCreative
      } catch (err: any) {
        // Extract error message from API response
        let message = 'Failed to create creative'
        if (err?.response?.data) {
          const errorData = err.response.data
          if (errorData.detail) {
            // Handle validation errors
            if (Array.isArray(errorData.detail)) {
              const validationErrors = errorData.detail.map((e: any) =>
                `${e.loc?.join('.')}: ${e.msg}`
              ).join(', ')
              message = `Validation error: ${validationErrors}`
            } else if (typeof errorData.detail === 'string') {
              message = errorData.detail
            } else {
              message = errorData.message || JSON.stringify(errorData.detail)
            }
          } else if (errorData.message) {
            message = errorData.message
          }
        } else if (err instanceof Error) {
          message = err.message
        }
        setError(message)
        console.error('Create creative error:', err)
        throw new Error(message)
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Get single creative
  const getCreative = useCallback(async (campaignId: string, creativeId: string) => {
    if (!campaignId) throw new Error('Campaign ID is required')
    if (!creativeId) throw new Error('Creative ID is required')
    try {
      const response = await apiClient.get(`/api/campaigns/${campaignId}/creatives/${creativeId}`)
      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch creative'
      setError(message)
      throw err
    }
  }, [])

  // Update creative
  const updateCreative = useCallback(
    async (creativeId: string, updates: Partial<CreateCreativeInput>) => {
      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.put(`/api/creatives/${creativeId}`, updates)
        const updated = response.data

        setCreatives((prev) =>
          prev.map((p) => (p.id === creativeId ? updated : p))
        )
        return updated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update creative'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  // Delete creative
  const deleteCreative = useCallback(async (campaignId: string, creativeId: string) => {
    if (!campaignId) throw new Error('Campaign ID is required')
    if (!creativeId) throw new Error('Creative ID is required')

    setLoading(true)
    setError(null)

    try {
      await apiClient.delete(`/api/campaigns/${campaignId}/creatives/${creativeId}`)
      setCreatives((prev) => prev.filter((p) => p.id !== creativeId))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete creative'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    creatives,
    loading,
    error,
    fetchCreatives,
    createCreative,
    getCreative,
    updateCreative,
    deleteCreative,
  }
}

