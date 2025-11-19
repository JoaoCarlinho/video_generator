import { useState, useCallback, useEffect } from 'react'
import { useAuth } from './useAuth'
import { apiClient } from '@/services/api'

export interface Brand {
  brand_id: string
  user_id: string
  brand_name: string
  brand_logo_url: string
  brand_guidelines_url: string
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export interface BrandStats {
  total_perfumes: number
  total_campaigns: number
  total_cost: number
}

export const useBrand = () => {
  const { user } = useAuth()
  const [brand, setBrand] = useState<Brand | null>(null)
  const [stats, setStats] = useState<BrandStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch current brand
  const fetchBrand = useCallback(async () => {
    if (!user) return

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get('/api/brands/me')
      setBrand(response.data)
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Failed to fetch brand'
      setError(message)
      console.error('Error fetching brand:', err)
    } finally {
      setLoading(false)
    }
  }, [user])

  // Fetch brand stats
  const fetchBrandStats = useCallback(async () => {
    if (!user) return

    try {
      const response = await apiClient.get('/api/brands/me/stats')
      setStats(response.data)
    } catch (err: any) {
      console.error('Error fetching brand stats:', err)
    }
  }, [user])

  // Onboard brand (create brand with logo and guidelines)
  const onboardBrand = useCallback(
    async (brandName: string, logoFile: File, guidelinesFile: File) => {
      if (!user) throw new Error('Not authenticated')

      setLoading(true)
      setError(null)

      try {
        const formData = new FormData()
        formData.append('brand_name', brandName)
        formData.append('logo', logoFile)
        formData.append('guidelines', guidelinesFile)

        const response = await apiClient.post('/api/brands/onboard', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })

        setBrand(response.data)
        return response.data
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Failed to onboard brand'
        setError(message)
        console.error('Error onboarding brand:', err)
        throw new Error(message)
      } finally {
        setLoading(false)
      }
    },
    [user]
  )

  // Load brand on mount
  useEffect(() => {
    if (user) {
      fetchBrand()
      fetchBrandStats()
    }
  }, [user, fetchBrand, fetchBrandStats])

  return {
    brand,
    stats,
    loading,
    error,
    fetchBrand,
    fetchBrandStats,
    onboardBrand,
  }
}

