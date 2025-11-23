import { useState, useCallback, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
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
  total_products: number
  total_campaigns: number
  total_cost: number
}

export const useBrand = () => {
  const { user } = useAuth()
  const location = useLocation()
  const [brand, setBrand] = useState<Brand | null>(null)
  const [stats, setStats] = useState<BrandStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const hasFetchedRef = useRef(false)
  const isOnboardingPage = location.pathname === '/onboarding'

  // Fetch current brand
  const fetchBrand = useCallback(async () => {
    if (!user) return

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get('/api/brands/me')
      setBrand(response.data)
    } catch (err: any) {
      // Handle 404 gracefully - user just hasn't completed onboarding yet
      if (err?.response?.status === 404) {
        setBrand(null)
        setError(null) // Don't treat 404 as an error
      } else {
      const message = err?.response?.data?.detail || err?.message || 'Failed to fetch brand'
      setError(message)
      console.error('Error fetching brand:', err)
      }
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
      // Handle 404 gracefully - user just hasn't completed onboarding yet
      if (err?.response?.status === 404) {
        setStats(null)
        // Don't log 404 as error - it's expected for users without brands
      } else {
      console.error('Error fetching brand stats:', err)
      }
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
        // Refresh brand stats after onboarding
        await fetchBrandStats()
        return response.data
      } catch (err: any) {
        // If 409 Conflict, brand already exists - fetch it instead
        if (err?.response?.status === 409) {
          // Brand already exists, fetch it
          await fetchBrand()
          await fetchBrandStats()
          // Still throw error so UI can handle it
          const message = err?.response?.data?.detail || 'Brand already exists'
          setError(message)
          throw new Error(message)
        } else {
        const message = err?.response?.data?.detail || err?.message || 'Failed to onboard brand'
        setError(message)
        console.error('Error onboarding brand:', err)
        throw new Error(message)
        }
      } finally {
        setLoading(false)
      }
    },
    [user, fetchBrand, fetchBrandStats]
  )

  // Load brand on mount
  // On onboarding page: fetch once to check if brand exists (for redirect)
  // On other pages: fetch normally
  useEffect(() => {
    if (!user) {
      return
    }
    
    // Only fetch once per session unless brand changes
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true
      fetchBrand()
      // Only fetch stats if not on onboarding page (to avoid 404 spam)
      if (!isOnboardingPage) {
      fetchBrandStats()
    }
    }
  }, [user, isOnboardingPage, fetchBrand, fetchBrandStats])
  
  // Reset fetch flag when brand is set (after onboarding)
  useEffect(() => {
    if (brand) {
      hasFetchedRef.current = true
    }
  }, [brand])

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

