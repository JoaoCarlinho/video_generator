import { useState, useCallback } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'

export type CampaignStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type VideoStyle = 'gold_luxe' | 'dark_elegance' | 'romantic_floral'

export interface Campaign {
  campaign_id: string
  product_id: string
  brand_id: string
  campaign_name: string
  creative_prompt: string
  selected_style: VideoStyle
  target_duration: number
  num_variations: number
  selected_variation_index?: number | null
  status: CampaignStatus
  progress: number
  cost: number
  error_message?: string | null
  campaign_json: Record<string, any>
  created_at: string
  updated_at: string
}

export interface CreateCampaignInput {
  product_id: string
  campaign_name: string
  creative_prompt: string
  selected_style: VideoStyle
  target_duration: number
  num_variations?: number
}

export interface PaginatedCampaigns {
  campaigns: Campaign[]
  total: number
  page: number
  limit: number
  pages: number
}

export const useCampaigns = () => {
  const { user } = useAuth()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch campaigns for a product
  const fetchCampaigns = useCallback(
    async (productId: string, page: number = 1, limit: number = 20) => {
      if (!user || !productId) return

      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.get<PaginatedCampaigns>('/api/campaigns', {
          params: { product_id: productId, page, limit },
        })
        setCampaigns(response.data.campaigns || [])
        return response.data
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to fetch campaigns'
        setError(message)
        console.error('Error fetching campaigns:', err)
        throw err
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
      const response = await apiClient.get<Campaign>(`/api/campaigns/${campaignId}`)
      return response.data
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to fetch campaign'
      setError(message)
      throw err
    }
  }, [])

  // Create campaign
  const createCampaign = useCallback(
    async (input: CreateCampaignInput) => {
      if (!user) throw new Error('Not authenticated')

      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.post<Campaign>('/api/campaigns', {
          product_id: input.product_id,
          campaign_name: input.campaign_name,
          creative_prompt: input.creative_prompt,
          selected_style: input.selected_style,
          target_duration: input.target_duration,
          num_variations: input.num_variations || 1,
        })

        setCampaigns((prev) => [response.data, ...prev])
        return response.data
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to create campaign'
        setError(message)
        console.error('Error creating campaign:', err)
        throw new Error(message)
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Delete campaign
  const deleteCampaign = useCallback(async (campaignId: string) => {
    setLoading(true)
    setError(null)

    try {
      await apiClient.delete(`/api/campaigns/${campaignId}`)
      setCampaigns((prev) => prev.filter((c) => c.campaign_id !== campaignId))
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to delete campaign'
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
    getCampaign,
    createCampaign,
    deleteCampaign,
  }
}

