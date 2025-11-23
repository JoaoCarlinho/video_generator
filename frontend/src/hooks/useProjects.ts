import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'
import type { AspectRatio, SceneBackground } from '@/types'

export interface Campaign {
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

interface CreateCampaignInput {
  title: string
  brief?: string
  brand_name: string
  mood?: string
  duration?: number
  aspect_ratio?: '9:16' | '1:1' | '16:9'
  product_image_url?: string
  productImages?: string[]
  sceneBackgrounds?: SceneBackground[]
  outputFormats?: AspectRatio[]
  logo_url?: string
  guidelines_url?: string
  creative_prompt?: string
  brand_description?: string
  target_audience?: string
  target_duration?: number
  // WAN 2.5: Video provider selection
  video_provider?: 'replicate' | 'ecs'
  // Phase 9: Product-specific fields
  perfume_name: string
  perfume_gender: 'masculine' | 'feminine' | 'unisex'
  // Phase 3: Multi-variation support
  num_variations?: 1 | 2 | 3 // Number of video variations (1-3)
}

export const useCampaigns = () => {
  const { user } = useAuth()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch all campaigns
  const fetchCampaigns = useCallback(async () => {
    if (!user) return

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get('/api/campaigns/')
      // API returns { campaigns: [...], total, limit, offset }
      setCampaigns(response.data.campaigns || [])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch campaigns'
      setError(message)
      console.error('Error fetching campaigns:', err)
    } finally {
      setLoading(false)
    }
  }, [user])

  // Create new campaign
  const createCampaign = useCallback(
    async (input: CreateCampaignInput) => {
      if (!user) throw new Error('Not authenticated')

      setLoading(true)
      setError(null)

      try {
        // Ensure video_provider defaults to "replicate" if not provided
        const payload = {
          ...input,
          video_provider: input.video_provider || 'replicate',
        }

        const response = await apiClient.post('/api/campaigns/', payload)
        const newCampaign = response.data

        setCampaigns((prev) => [newCampaign, ...prev])

        // Log provider selection for analytics
        console.log('[Campaign Created]', {
          campaignId: newCampaign.id,
          provider: newCampaign.video_provider || payload.video_provider,
          timestamp: new Date().toISOString(),
        })

        return newCampaign
      } catch (err: any) {
        // Extract error message from API response
        let message = 'Failed to create campaign'
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
        console.error('Create campaign error:', err)
        throw new Error(message)
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Get single campaign
  const getCampaign = useCallback(async (campaignId: string) => {
    if (!campaignId) throw new Error('Campaign ID is required')
    try {
      const response = await apiClient.get(`/api/campaigns/${campaignId}`)
      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch campaign'
      setError(message)
      throw err
    }
  }, [])

  // Update campaign
  const updateCampaign = useCallback(
    async (campaignId: string, updates: Partial<CreateCampaignInput>) => {
      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.put(`/api/campaigns/${campaignId}`, updates)
        const updated = response.data

        setCampaigns((prev) =>
          prev.map((p) => (p.id === campaignId ? updated : p))
        )
        return updated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update campaign'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  // Delete campaign
  const deleteCampaign = useCallback(async (campaignId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.delete(`/api/campaigns/${campaignId}`)
      setCampaigns((prev) => prev.filter((p) => p.id !== campaignId))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete campaign'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    campaigns,
    loading,
    error,
    fetchCampaigns,
    createCampaign,
    getCampaign,
    updateCampaign,
    deleteCampaign,
  }
}

